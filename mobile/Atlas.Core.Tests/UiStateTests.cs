using Atlas.Core;
using Atlas.UI;
using Atlas.UI.Components;
using Microsoft.AspNetCore.Components.Web;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using Xunit;

namespace Atlas.Core.Tests;
public sealed class UiStateTests
{
    [Fact]
    public async Task SetupUnlocksAfterStartupAndTracksSubsequentBusyChanges()
    {
        var directory=Path.Combine(Path.GetTempPath(),"atlas-ui-test-"+Guid.NewGuid());
        var credentials=new CredentialsStub();
        using var repository=new AtlasRepository(new CacheStore(Path.Combine(directory,"cache.db")));
        var state=new AppState(repository,credentials,new FilesStub());
        using var services=new ServiceCollection().AddLogging().AddSingleton(state).BuildServiceProvider();
        await using var renderer=new HtmlRenderer(services,services.GetRequiredService<ILoggerFactory>());
        try
        {
            var rendered=await renderer.Dispatcher.InvokeAsync(()=>renderer.BeginRenderingComponent<AtlasRoot>());
            var initial=await renderer.Dispatcher.InvokeAsync(rendered.ToHtmlString);
            Assert.Matches("id=\"token\"[^>]*disabled",initial);
            credentials.Loaded.SetResult(null);
            await rendered.QuiescenceTask;
            var ready=await renderer.Dispatcher.InvokeAsync(rendered.ToHtmlString);
            Assert.DoesNotMatch("id=\"token\"[^>]*disabled",ready);
            Assert.DoesNotContain("Toggle navigation",ready);
            var gate=new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
            Task<bool>? operation=null;
            await renderer.Dispatcher.InvokeAsync(()=>{operation=state.Run(()=>gate.Task);});
            var busy=await renderer.Dispatcher.InvokeAsync(rendered.ToHtmlString);
            Assert.Matches("id=\"token\"[^>]*disabled",busy);
            gate.SetResult();await operation!;
            var completed=await renderer.Dispatcher.InvokeAsync(rendered.ToHtmlString);
            Assert.DoesNotMatch("id=\"token\"[^>]*disabled",completed);
        }
        finally
        {
            Microsoft.Data.Sqlite.SqliteConnection.ClearAllPools();
            Directory.Delete(directory,true);
        }
    }
    private sealed class CredentialsStub:ICredentialStore
    {
        public TaskCompletionSource<Credentials?> Loaded {get;}=new(TaskCreationOptions.RunContinuationsAsynchronously);
        public Task<Credentials?> LoadAsync()=>Loaded.Task;
        public Task SaveAsync(Credentials value)=>Task.CompletedTask;
        public void Clear(){}
    }
    private sealed class FilesStub:IDeviceFiles
    {
        public Task<(string Name,byte[] Content)?> PickAsync()=>Task.FromResult<(string,byte[])?>(null);
        public Task SaveAsync(string name,byte[] content)=>Task.CompletedTask;
        public Task<bool> ConfirmAsync(string title,string message)=>Task.FromResult(false);
    }
}
