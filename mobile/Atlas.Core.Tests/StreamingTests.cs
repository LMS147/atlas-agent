using System.Net;
using System.Text;
using System.Text.Json;
using Atlas.Core;
using Xunit;
namespace Atlas.Core.Tests;
public sealed class StreamingTests
{
    private const string Token="stream-test-token-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx";
    private static string Event(string kind,object value)=>$"event: {kind}\r\ndata: {JsonSerializer.Serialize(value,AtlasApi.Json)}\r\n\r\n";
    private static HttpResponseMessage Sse(string text)=>new HttpResponseMessage(HttpStatusCode.OK){Content=new StreamContent(new ByteFragments(Encoding.UTF8.GetBytes(text)))}.WithType();
    [Fact] public async Task FragmentedUtf8ReportsProgressBeforeCompletedReply()
    {
        var content=Event("status",new{request_id="r1",phase="thinking"})+": heartbeat\r\n\r\n"+Event("progress",new{request_id="r1",phase="replying",text="Hello 世界"})+Event("complete",new{request_id="r1",reply="Hello 世界!"});
        using var api=new AtlasApi("https://example.test/",Token,new Handler(_=>Sse(content)));
        var progress=new List<(string,string)>();
        var reply=await api.StreamChatAsync(new{},"r1",(phase,text)=>progress.Add((phase,text)));
        Assert.Equal("Hello 世界!",reply);Assert.Contains(("replying","Hello 世界"),progress);
    }
    [Fact] public async Task TruncatedOrWrongRequestStreamsNeverCountAsCompleted()
    {
        foreach(var content in new[]{Event("progress",new{request_id="r1",phase="replying",text="Partial"}),Event("complete",new{request_id="other",reply="Wrong"})})
        {
            var count=0;using var api=new AtlasApi("https://example.test/",Token,new Handler(_=>{count++;return Sse(content);}));
            await Assert.ThrowsAsync<IOException>(()=>api.StreamChatAsync(new{},"r1",(_,_)=>{}));Assert.Equal(1,count);
        }
    }
    [Fact] public async Task InterruptedStreamKeepsDurableRecoveryAndDoesNotReplayInference()
    {
        var dir=Path.Combine(Path.GetTempPath(),"atlas-stream-"+Guid.NewGuid());var inference=0;
        HttpResponseMessage Json(object value)=>new(HttpStatusCode.OK){Content=new StringContent(JsonSerializer.Serialize(value,AtlasApi.Json),Encoding.UTF8,"application/json")};
        using var repo=new AtlasRepository(new CacheStore(Path.Combine(dir,"cache.db")),(url,token)=>new AtlasApi(url,token,new Handler(req=>
        {
            var path=req.RequestUri!.AbsolutePath;
            if(path.EndsWith("/health"))return Json(new{status="ok",streaming_chat=true});
            if(path.EndsWith("/conversations"))return Json(new[]{new Conversation("chat","Test",1,1,0,"")});
            if(path.EndsWith("/chat/stream")){inference++;return Sse(": heartbeat\n\n");}
            if(path.Contains("/requests/"))return Json(new{request_id=path.Split('/').Last(),status="done",reply="Saved reply"});
            return Json(new Conversation("chat","Test",1,2,2,"Saved reply"));
        })));
        try
        {
            await repo.ConnectAsync("https://example.test/",Token);
            await Assert.ThrowsAsync<IOException>(()=>repo.SendAsync("Hello"));
            var msg=Assert.Single(repo.Messages);Assert.Equal(Delivery.Recoverable,msg.Delivery);Assert.Equal("",repo.StreamText);
            await repo.RecoverAsync(msg.Id);Assert.Equal(1,inference);
            Assert.Equal("Saved reply",repo.Messages.Single(x=>x.Role=="assistant").Text);
        }
        finally{Microsoft.Data.Sqlite.SqliteConnection.ClearAllPools();Directory.Delete(dir,true);}
    }
    private sealed class Handler(Func<HttpRequestMessage,HttpResponseMessage> handle):HttpMessageHandler
    {
        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request,CancellationToken ct)=>Task.FromResult(handle(request));
    }
    private sealed class ByteFragments(byte[] bytes):MemoryStream(bytes)
    {
        public override ValueTask<int> ReadAsync(Memory<byte> buffer,CancellationToken ct=default)=>base.ReadAsync(buffer[..Math.Min(1,buffer.Length)],ct);
    }
}
internal static class StreamResponseExtensions
{
    public static HttpResponseMessage WithType(this HttpResponseMessage response){response.Content.Headers.ContentType=new("text/event-stream");return response;}
}
