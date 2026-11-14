using Atlas.Core;
using Atlas.UI;
using System.Net;
using System.Net.Http.Json;
using Xunit;
namespace Atlas.Core.Tests;
public sealed class CompanionPresenceTests
{
    [Fact]
    public async Task ThinkingRequiresAnActiveRequestAndPendingMessage()
    {
        var folder=Path.Combine(Path.GetTempPath(),"atlas-presence-"+Guid.NewGuid());
        var cache=new CacheStore(Path.Combine(folder,"cache.db"));
        using var repo=new AtlasRepository(cache,(url,token)=>new AtlasApi(url,token,new Server()));
        var state=new AppState(repo,new CredentialsStub(),new FilesStub());
        try
        {
            await repo.ConnectAsync("https://example.test",new string('x',32));
            Assert.Equal("idle",CompanionPresence.Mode(state));
            var gate=new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
            var operation=state.Run(()=>gate.Task);
            Assert.Equal("idle",CompanionPresence.Mode(state));
            var message=new LocalMessage("m1","c1","r1","user","Hello",1,Delivery.Pending);
            cache.Put(repo.Scope,"messages",message.Id,message);
            Assert.Equal("thinking",CompanionPresence.Mode(state));
            gate.SetResult();await operation;
            Assert.Equal("idle",CompanionPresence.Mode(state));
            cache.Put(repo.Scope,"messages",message.Id,message with {Delivery=Delivery.Recoverable});
            Assert.Equal("idle",CompanionPresence.Mode(state));
        }
        finally{Microsoft.Data.Sqlite.SqliteConnection.ClearAllPools();Directory.Delete(folder,true);}
    }
    private sealed class Server:HttpMessageHandler
    {
        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request,CancellationToken ct)
        {
            object data=request.RequestUri!.AbsolutePath.EndsWith("health")?new Health("ok"):new[]{new Conversation("c1","Chat",1,1,0,"")};
            return Task.FromResult(new HttpResponseMessage(HttpStatusCode.OK){Content=JsonContent.Create(data,options:AtlasApi.Json)});
        }
    }
    private sealed class CredentialsStub:ICredentialStore{public Task<Credentials?> LoadAsync()=>Task.FromResult<Credentials?>(null);public Task SaveAsync(Credentials c)=>Task.CompletedTask;public void Clear(){}}
    private sealed class FilesStub:IDeviceFiles{public Task<(string Name,byte[] Content)?> PickAsync()=>Task.FromResult<(string,byte[])?>(null);public Task SaveAsync(string n,byte[] b)=>Task.CompletedTask;public Task<bool> ConfirmAsync(string t,string m)=>Task.FromResult(false);}
}
