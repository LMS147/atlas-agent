using System.Net;
using System.Text;
using System.Text.Json;
using Atlas.Core;
using Xunit;
namespace Atlas.Core.Tests;

public sealed class RepositoryTests : IDisposable
{
    private const string Token="test-atlas-token-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx";
    private readonly string directory=Path.Combine(Path.GetTempPath(),"atlas-test-"+Guid.NewGuid());
    private readonly List<(string Method,string Path,string Body,string? Auth)> calls=[];
    private Func<HttpRequestMessage,string,HttpResponseMessage> response=(_,_)=>Json(new{});
    private CacheStore Store()=>new(Path.Combine(directory,"cache.sqlite3"));
    private AtlasRepository Repo()=>new(Store(),(url,token)=>new AtlasApi(url,token,new Handler(async request=>
    {
        var body=request.Content is null?"":await request.Content.ReadAsStringAsync();
        calls.Add((request.Method.Method,request.RequestUri!.PathAndQuery,body,request.Headers.Authorization?.ToString()));
        if(request.RequestUri.AbsolutePath=="/api/v1/health")return Json(new{status="ok"});
        if(request.RequestUri.AbsolutePath=="/api/v1/conversations")return Json(new[]{new Conversation("chat-test","Test",1,1,0,"")});
        if(request.RequestUri.AbsolutePath=="/api/v1/conversations/chat-test")return Json(new Conversation("chat-test","Test",1,2,2,"Reply"));
        return response(request,body);
    })));
    private static HttpResponseMessage Json(object body,int status=200)=>new((HttpStatusCode)status){Content=new StringContent(JsonSerializer.Serialize(body,AtlasApi.Json),Encoding.UTF8,"application/json")};
    private static async Task Connect(AtlasRepository repo,string token=Token)=>await repo.ConnectAsync("https://atlas.example/",token);
    private List<(string Method,string Path,string Body,string? Auth)> Chats=>calls.Where(x=>x.Path=="/api/v1/chat").ToList();

    [Fact] public void OnlyExplicitHttpsWithoutEmbeddedCredentialsIsAccepted()
    {
        Assert.Equal("https://atlas.example/",AtlasApi.Normalize(" https://atlas.example "));
        foreach(var url in new[]{"http://atlas.example","https://user:secret@atlas.example/","https://atlas.example/?token=x","https://atlas.example/#x"})Assert.Throws<ArgumentException>(()=>AtlasApi.Normalize(url));
    }
    [Fact] public async Task DroppedReplyIsPersistedAndRecoveredAfterReopenWithoutAnotherInference()
    {
        using(var first=Repo())
        {
            await Connect(first);response=(_,_)=>throw new HttpRequestException("simulated dropped response");
            await Assert.ThrowsAsync<HttpRequestException>(()=>first.SendAsync("Hello"));
            Assert.Equal(Delivery.Recoverable,first.Messages.Single().Delivery);
        }
        using var restored=Repo();await Connect(restored);
        var msg=restored.Messages.Single();response=(_,_)=>Json(new RequestStatus(msg.RequestId,"done","Saved answer"));
        await restored.RecoverAsync(msg.Id);
        Assert.Single(Chats);Assert.Equal(2,restored.Messages.Count);Assert.All(restored.Messages,x=>Assert.Equal(Delivery.Sent,x.Delivery));
        Assert.Contains(calls,x=>x.Method=="GET" && x.Path.Contains("/requests/"));
        Assert.All(calls,x=>Assert.Equal("Bearer "+Token,x.Auth));
        Assert.True(JsonDocument.Parse(Chats.Single().Body).RootElement.GetProperty("require_existing").GetBoolean());
    }
    [Fact] public async Task MissingRequestRetriesSameIdWhileProviderFailureNeedsFreshId()
    {
        using var repo=Repo();await Connect(repo);response=(_,_)=>throw new HttpRequestException();
        await Assert.ThrowsAsync<HttpRequestException>(()=>repo.SendAsync("Question"));var original=repo.Messages.Single();
        response=(_,_)=>Json(new RequestStatus(original.RequestId,"not_found",null));await repo.RecoverAsync(original.Id);
        Assert.Equal(Delivery.NotReceived,repo.Messages.Single().Delivery);
        response=(_,_)=>Json(new{},502);await Assert.ThrowsAsync<AtlasApiException>(()=>repo.RetryAsync(original.Id,false));
        var same=JsonDocument.Parse(Chats.Last().Body).RootElement.GetProperty("request_id").GetString();Assert.Equal(original.RequestId,same);
        await Assert.ThrowsAsync<ArgumentException>(()=>repo.RetryAsync(original.Id,false));
        response=(_,_)=>Json(new{reply="Done"});await repo.RetryAsync(original.Id,true);
        Assert.NotEqual(original.RequestId,repo.Messages.First(x=>x.Role=="user").RequestId);Assert.Equal(2,repo.Messages.Count);
    }
    [Fact] public async Task PendingStatusNeverSendsAnotherChat()
    {
        using var repo=Repo();await Connect(repo);response=(_,_)=>throw new HttpRequestException();
        await Assert.ThrowsAsync<HttpRequestException>(()=>repo.SendAsync("Question"));var msg=repo.Messages.Single();
        response=(_,_)=>Json(new RequestStatus(msg.RequestId,"pending",null));await repo.RecoverAsync(msg.Id);
        Assert.Equal(Delivery.Recoverable,repo.Messages.Single().Delivery);Assert.Single(Chats);
        await Assert.ThrowsAsync<ArgumentException>(()=>repo.SendAsync("Another question"));Assert.Single(Chats);
    }
    [Fact] public async Task HistoryMergesByRequestAndTombstoneRemovesLocalTranscript()
    {
        using var repo=Repo();await Connect(repo);var rid=Guid.NewGuid().ToString();
        response=(_,_)=>Json(new MessagePage([new(1,"a",rid,"user","Question",10),new(2,"b",rid,"assistant","Answer",11)],true,1));
        await repo.HistoryAsync();await repo.HistoryAsync();Assert.Equal(2,repo.Messages.Count);Assert.True(repo.Current!.HasMore);
        // Switch the factory-independent response by using a fresh API handler for a server tombstone.
        using var tombstone=new AtlasRepository(Store(),(url,token)=>new AtlasApi(url,token,new Handler(request=>Task.FromResult(request.RequestUri!.AbsolutePath.EndsWith("health")?Json(new{status="ok"}):Json(new[]{new Conversation("chat-test","Deleted",1,2,0,"",true)})))));
        await Connect(tombstone);Assert.Empty(tombstone.Conversations);Assert.Empty(Store().All<LocalMessage>(repo.Scope,"messages"));
    }
    [Fact] public async Task CacheDoesNotLeakAcrossTokensAndCanOpenOffline()
    {
        using(var first=Repo()){await Connect(first);response=(_,_)=>Json(new{reply="Private answer"});await first.SendAsync("Private question");}
        using var second=Repo();await Connect(second,Token+"other");Assert.Empty(second.Messages);
        using var offline=new AtlasRepository(Store(),(url,token)=>new AtlasApi(url,token,new Handler(_=>throw new HttpRequestException())));
        await Connect(offline);Assert.True(offline.Offline);Assert.Equal(2,offline.Messages.Count);
        await Assert.ThrowsAsync<HttpRequestException>(()=>offline.ConnectAsync("https://different.example/",Token));
    }
    [Fact] public async Task InterruptedPendingIsRecoveredWithoutSilentResend()
    {
        using var repo=Repo();await Connect(repo);var id=Guid.NewGuid().ToString();
        Store().Put(repo.Scope,"messages",id,new LocalMessage(id,repo.ConversationId,id,"user","Interrupted",1,Delivery.Pending));
        using var reopened=Repo();await Connect(reopened);Assert.Equal(Delivery.Recoverable,reopened.Messages.Single().Delivery);Assert.Empty(Chats);
    }
    [Fact] public async Task BinaryTransferIsBoundedAndPreservesBytes()
    {
        var bytes=new byte[]{0,1,255,2};using var api=new AtlasApi("https://atlas.example/",Token,new Handler(async request=>
        {
            Assert.Equal("Bearer "+Token,request.Headers.Authorization!.ToString());
            if(request.Method==HttpMethod.Post){Assert.Equal(bytes,await request.Content!.ReadAsByteArrayAsync());return Json(new{});}
            return new HttpResponseMessage(HttpStatusCode.OK){Content=new ByteArrayContent(bytes)};
        }));
        await api.UploadAsync("binary.bin",bytes);Assert.Equal(bytes,await api.DownloadAsync("workspace/binary.bin"));
        await Assert.ThrowsAsync<ArgumentException>(()=>AtlasApi.ReadBoundedAsync(new MemoryStream(new byte[AtlasApi.MaxFileBytes+1])));
    }
    [Fact] public async Task MetricsKeepRestrictedValuesNullAndFileEditsIncludeRevision()
    {
        using var repo=Repo();await Connect(repo);response=(request,body)=>request.Method==HttpMethod.Put?Json(new FileItem("test.txt","workspace/test.txt",false,3,true)):Json(new Atlas.Core.Monitoring(1,null,1.5,null,null,null,null,new(1,2,3,4,0,1),["device CPU"]));
        var metrics=await repo.MonitoringAsync();Assert.Null(metrics.Ram);Assert.Null(metrics.DeviceCpuPercent);
        var revision=new string('a',64);await repo.EditFileAsync(new FileDocument("workspace/test.txt","old",revision,true),"new");
        var edit=JsonDocument.Parse(calls.Last().Body);Assert.Equal(revision,edit.RootElement.GetProperty("revision").GetString());
    }
    [Fact] public async Task MemoryChangesRefreshThePersistentCacheAndCompactionUsesPreviewRevision()
    {
        using var repo=Repo();await Connect(repo);
        var rows=new List<MemoryItem>();var revision=new string('b',64);
        response=(request,body)=>
        {
            if(request.RequestUri!.AbsolutePath.EndsWith("memory/compact"))
            {
                if(request.Method==HttpMethod.Post)Assert.Equal(revision,JsonDocument.Parse(body).RootElement.GetProperty("revision").GetString());
                return Json(new CompactPlan(revision,100,80,1));
            }
            if(request.Method==HttpMethod.Get)return Json(rows);
            if(request.Method==HttpMethod.Delete){rows.Clear();return new HttpResponseMessage(HttpStatusCode.NoContent);}
            var payload=JsonDocument.Parse(body).RootElement;
            rows.Clear();rows.Add(new MemoryItem("saved",payload.GetProperty("section").GetString()!,payload.GetProperty("fact").GetString()!));
            return request.Method==HttpMethod.Post?Json(rows.Single(),201):new HttpResponseMessage(HttpStatusCode.NoContent);
        };
        await repo.SaveMemoryAsync(null,"Projects","  Keep   this fact  ");Assert.Equal("Keep this fact",repo.Memories.Single().Fact);
        await repo.SaveMemoryAsync("saved","People","Updated fact");Assert.Equal("People",Store().All<MemoryItem>(repo.Scope,"memory").Single().Section);
        var preview=await repo.CompactPreviewAsync();await repo.CompactAsync(preview.Revision);
        await repo.DeleteMemoryAsync("saved");Assert.Empty(repo.Memories);
    }
    public void Dispose(){Microsoft.Data.Sqlite.SqliteConnection.ClearAllPools();if(Directory.Exists(directory))Directory.Delete(directory,true);}
    private sealed class Handler(Func<HttpRequestMessage,Task<HttpResponseMessage>> callback):HttpMessageHandler
    {
        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request,CancellationToken ct)=>callback(request);
    }
}
