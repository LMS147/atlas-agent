using Atlas.Core;
using Atlas.UI;
using Atlas.UI.Components;
using Microsoft.AspNetCore.Components.Web;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using System.Net;
using System.Net.Http.Json;
var output=Path.GetFullPath(args.FirstOrDefault()??"visual-results");Directory.CreateDirectory(output);
var cache=new CacheStore(Path.Combine(Path.GetTempPath(),"atlas-visual-"+Guid.NewGuid(),"cache.db"));
var mock=new Mock();
using var repo=new AtlasRepository(cache,(url,token)=>new AtlasApi(url,token,mock));
var state=new AppState(repo,new Creds(),new Files());
using var services=new ServiceCollection().AddLogging().AddSingleton(state).BuildServiceProvider();
await using var renderer=new HtmlRenderer(services,services.GetRequiredService<ILoggerFactory>());
var root=await renderer.Dispatcher.InvokeAsync(()=>renderer.RenderComponentAsync<AtlasRoot>());
async Task Save(string name){var html=await renderer.Dispatcher.InvokeAsync(root.ToHtmlString);await File.WriteAllTextAsync($"{output}/{name}.html","<!DOCTYPE html><html><head><meta charset=\"utf-8\"><meta name=viewport content=\"width=device-width,initial-scale=1\"><link rel=stylesheet href=\"atlas.css\"></head><body>"+html+"</body></html>");}
await Save("setup");
Task<bool>? busy=null;var gate=new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
await renderer.Dispatcher.InvokeAsync(()=>{busy=state.Run(()=>gate.Task);});await Save("setup-loading");gate.SetResult();await busy!;
await renderer.Dispatcher.InvokeAsync(()=>state.Run(()=>throw new HttpRequestException("Unavailable")));await Save("setup-error");
await renderer.Dispatcher.InvokeAsync(async()=>{await repo.ConnectAsync("https://example.test/",new string('x',32));await state.NavigateAsync("Chat");});
await Save("chat");
cache.Put(repo.Scope,"messages","m1",new LocalMessage("m1","c1","r1","user","Help me turn an idea into a clear plan.",1));
cache.Put(repo.Scope,"messages","m2",new LocalMessage("m2","c1","r1","assistant","Let’s start with the outcome. What would you like to accomplish, and what does a successful first version look like?",2));
await renderer.Dispatcher.InvokeAsync(state.Notify);await Save("conversation");
cache.Put(repo.Scope,"conversations","c1",repo.Current! with {ServerAvailable=false});
await renderer.Dispatcher.InvokeAsync(state.Notify);await Save("cached-chat");
cache.Put(repo.Scope,"conversations","c1",repo.Current! with {ServerAvailable=true});
await renderer.Dispatcher.InvokeAsync(()=>state.NavigateAsync("Memory"));await Save("memory-empty");
mock.Populated=true;await renderer.Dispatcher.InvokeAsync(()=>state.NavigateAsync("Memory"));await Save("memory");
await renderer.Dispatcher.InvokeAsync(()=>state.NavigateAsync("Files"));await Save("files");
await renderer.Dispatcher.InvokeAsync(()=>state.NavigateAsync("Atlas"));await Save("companion");
await renderer.Dispatcher.InvokeAsync(()=>state.NavigateAsync("Tools"));await Save("tools");
await renderer.Dispatcher.InvokeAsync(()=>state.NavigateAsync("Profile"));await Save("profile");
await renderer.Dispatcher.InvokeAsync(()=>state.NavigateAsync("Settings"));await Save("settings");
await renderer.Dispatcher.InvokeAsync(()=>state.SetDrawer(true));await Save("drawer");
await renderer.Dispatcher.InvokeAsync(()=>state.SetDrawer(false));
await File.WriteAllTextAsync(Path.Combine(output,"3d.html"),"""
<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="atlas.css"></head><body><div class="atlas-character"><div id="stage" class="atlas-stage"><canvas id="canvas"></canvas></div></div><script type="module">import {buildAtlas} from './_content/Atlas.UI/atlas-3d.js';window.atlas=buildAtlas(document.getElementById('canvas'),document.getElementById('stage'));</script></body></html>
""");
sealed class Mock:HttpMessageHandler
{
    public bool Populated;
    protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage req,CancellationToken ct)
    {
        var path=req.RequestUri!.AbsolutePath;
        object value=path.EndsWith("health")?new Health("ok"):
            path.EndsWith("memory")?(Populated?new[]{new MemoryItem("a","Projects","Keep Atlas focused on conversations, memories, and personal tasks."),new MemoryItem("b","User Preferences","Use concise explanations and practical next steps.")}:Array.Empty<MemoryItem>()):
            path.EndsWith("files")?new[]{new FileItem("workspace","workspace",true,0,true),new FileItem("An exceptionally long workspace document filename with important project notes.md","workspace/notes.md",false,1830,true),new FileItem("AGENT.md","AGENT.md",false,946,false)}:
            path.EndsWith("agent")?new Profile("Atlas","# Atlas\n\nYour **personal AI companion** for thinking, creating, and getting things done.\n\n## How I help\n\n- Explore ideas and make plans\n- Remember useful context\n- Work with your documents\n\n## Your workspace\n\nYour server. Your memories. Your choices."):
            new[]{new Conversation("c1","A fresh perspective",1,1,0,"")};
        return Task.FromResult(new HttpResponseMessage(HttpStatusCode.OK){Content=JsonContent.Create(value,options:AtlasApi.Json)});
    }
}
sealed class Creds:ICredentialStore{public Task<Credentials?> LoadAsync()=>Task.FromResult<Credentials?>(null);public Task SaveAsync(Credentials c)=>Task.CompletedTask;public void Clear(){}}
sealed class Files:IDeviceFiles{public Task<(string Name,byte[] Content)?> PickAsync()=>Task.FromResult<(string,byte[])?>(null);public Task SaveAsync(string n,byte[] b)=>Task.CompletedTask;public Task<bool> ConfirmAsync(string t,string m)=>Task.FromResult(false);}
