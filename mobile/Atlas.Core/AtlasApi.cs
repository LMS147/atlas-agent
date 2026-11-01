using System.Net;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text.Json;

namespace Atlas.Core;

public sealed class AtlasApi : IDisposable
{
    public const string DefaultUrl = "https://atlas-api-a9s1.onrender.com/";
    public const int MaxFileBytes = 5 * 1024 * 1024;
    public static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web) { PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower };
    private readonly HttpClient client;
    private readonly string token;
    public string Url { get; }
    public AtlasApi(string url, string accessToken, HttpMessageHandler? handler = null)
    {
        Url = Normalize(url);
        token = accessToken.Trim();
        if (token.Length < 32 || token.Any(c => c < 33 || c > 126)) throw new ArgumentException("Enter your Atlas token (at least 32 printable characters, without spaces).");
        client = new HttpClient(handler ?? new HttpClientHandler { AllowAutoRedirect = false, UseCookies = false }) { BaseAddress = new Uri(Url), Timeout = TimeSpan.FromSeconds(100) };
    }
    public static string Normalize(string raw)
    {
        if (!Uri.TryCreate(raw.Trim(), UriKind.Absolute, out var uri) || uri.Scheme != "https" || !string.IsNullOrEmpty(uri.UserInfo) || !string.IsNullOrEmpty(uri.Query) || !string.IsNullOrEmpty(uri.Fragment))
            throw new ArgumentException("Use an HTTPS URL without credentials, a query or fragment.");
        return uri.AbsoluteUri.TrimEnd('/') + "/";
    }
    public async Task<T> JsonAsync<T>(HttpMethod method, string path, object? body = null, CancellationToken ct = default)
    {
        using var timeout = CancellationTokenSource.CreateLinkedTokenSource(ct);
        timeout.CancelAfter(TimeSpan.FromSeconds(100));
        using var response = await SendAsync(method, path, body is null ? null : JsonContent.Create(body, options: Json), timeout.Token);
        if (response.StatusCode == HttpStatusCode.NoContent) return default!;
        return await response.Content.ReadFromJsonAsync<T>(Json, timeout.Token) ?? throw new IOException("Atlas returned an empty response.");
    }
    public async Task EmptyAsync(HttpMethod method, string path, object? body = null)
    {
        using var response = await SendAsync(method, path, body is null ? null : JsonContent.Create(body, options: Json), default);
    }
    private async Task<HttpResponseMessage> SendAsync(HttpMethod method, string path, HttpContent? content, CancellationToken ct)
    {
        using var request = new HttpRequestMessage(method, "api/v1/" + path) { Content = content };
        request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);
        // No redirect following and no automatic retries: chat/tool effects must not be duplicated.
        var response = await client.SendAsync(request, HttpCompletionOption.ResponseHeadersRead, ct);
        if (!response.IsSuccessStatusCode)
        {
            var seconds = response.Headers.RetryAfter?.Delta?.TotalSeconds ?? 30;
            var error = new AtlasApiException((int)response.StatusCode, Math.Clamp((int)seconds, 1, 3600));
            response.Dispose();
            throw error;
        }
        return response;
    }
    public async Task<string> StreamChatAsync(object body,string requestId,Action<string,string> progress,CancellationToken ct=default)
    {
        using var timeout=CancellationTokenSource.CreateLinkedTokenSource(ct);
        timeout.CancelAfter(TimeSpan.FromSeconds(100));
        using var response=await SendAsync(HttpMethod.Post,"chat/stream",JsonContent.Create(body,options:Json),timeout.Token);
        if(response.Content.Headers.ContentType?.MediaType!="text/event-stream")throw new IOException("Atlas returned an invalid stream. Check for the saved reply.");
        using var input=await response.Content.ReadAsStreamAsync(timeout.Token);
        using var reader=new StreamReader(input,System.Text.Encoding.UTF8);
        string kind="";var data=new System.Text.StringBuilder();var line=new System.Text.StringBuilder();
        var buffer=new char[2048];long received=0;
        while(true)
        {
            var count=await reader.ReadAsync(buffer.AsMemory(),timeout.Token);
            if(count==0)break;
            received+=count;if(received>32*1024*1024)throw new IOException("Atlas stream exceeded limits. Check the saved reply.");
            for(var i=0;i<count;i++)
            {
                var c=buffer[i];
                if(c!='\n'){line.Append(c);if(line.Length>512*1024)throw new IOException("Stream event exceeded limits.");continue;}
                var value=line.ToString().TrimEnd('\r');line.Clear();
                if(value.Length==0)
                {
                    if(data.Length>0)
                    {
                        var e=JsonSerializer.Deserialize<ChatStreamEvent>(data.ToString(),Json)??throw new IOException("Invalid stream event.");
                        if(e.RequestId!=requestId)throw new IOException("Stream request did not match this message.");
                        if(kind=="complete")return !string.IsNullOrWhiteSpace(e.Reply)&&e.Reply.Length<=65536?e.Reply:throw new IOException("Invalid completed reply.");
                        if(kind=="error")throw new AtlasApiException(e.Status??500);
                        if(kind is "progress" or "status")
                        {
                            if(e.Phase is not ("thinking" or "replying") || (e.Text?.Length??0)>65536)throw new IOException("Invalid progress event.");
                            progress(e.Phase,e.Text??"");
                        }
                    }
                    kind="";data.Clear();
                }
                else if(value.StartsWith("event:",StringComparison.Ordinal))kind=value[6..].Trim();
                else if(value.StartsWith("data:",StringComparison.Ordinal))
                {
                    data.Append(value[5..].TrimStart(' '));data.Append('\n');
                    if(data.Length>512*1024)throw new IOException("Stream event exceeded limits.");
                }
            }
        }
        throw new IOException("Reply stream interrupted. Check for the saved reply before retrying.");
    }
    private sealed record ChatStreamEvent(string RequestId,string? Phase,string? Text,string? Reply,int? Status);

    public async Task UploadAsync(string name, byte[] bytes)
    {
        if (bytes.Length > MaxFileBytes) throw new ArgumentException("Uploads support up to 5 MiB.");
        using var content = new ByteArrayContent(bytes);
        content.Headers.ContentType = new MediaTypeHeaderValue("application/octet-stream");
        using var response = await SendAsync(HttpMethod.Post, "files/upload?name=" + Uri.EscapeDataString(name), content, default);
    }
    public async Task<byte[]> DownloadAsync(string path)
    {
        using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(100));
        using var response = await SendAsync(HttpMethod.Get, "files/content?path=" + Uri.EscapeDataString(path), null, timeout.Token);
        using var stream = await response.Content.ReadAsStreamAsync();
        return await ReadBoundedAsync(stream, timeout.Token);
    }
    public static async Task<byte[]> ReadBoundedAsync(Stream stream, CancellationToken ct = default)
    {
        using var output = new MemoryStream();
        var buffer = new byte[8192];
        int count;
        while ((count = await stream.ReadAsync(buffer, ct)) != 0)
        {
            if (output.Length + count > MaxFileBytes) throw new ArgumentException("File exceeds 5 MiB.");
            output.Write(buffer, 0, count);
        }
        return output.ToArray();
    }
    public void Dispose() => client.Dispose();
}
public sealed class AtlasApiException(int status, int retryAfter = 30) : Exception(status switch
{
    401 or 403 => "Access rejected. Check your Atlas token and server permissions.",
    404 => "This item or API endpoint is unavailable. Refresh and check the server version.",
    409 => "The item changed or the request cannot be safely repeated. Refresh and check before trying again.",
    410 => "This conversation was deleted on the server. Start another chat.",
    413 => "File too large: transfers support 5 MiB and text editing supports 256 KiB.",
    415 => "Binary file: use Download to open it with another app.",
    422 => "The server rejected the input. Check its format and length.",
    429 => $"The AI provider is rate limited. Wait {retryAfter} seconds before sending again.",
    502 => "The AI provider is unavailable. Check the Groq key and model on the server.",
    504 => "The AI provider timed out. Check saved memory before sending a fresh request.",
    _ => $"Atlas returned HTTP {status}. The operation may not have completed."
}) { public int Status { get; } = status; }
