using Atlas.Core;
namespace Atlas.UI;

/// <summary>Shared C# presentation state; native capabilities are injected at the host.</summary>
public sealed class AppState(AtlasRepository repository, ICredentialStore credentials, IDeviceFiles files)
{
    public AtlasRepository Repo { get; } = repository;
    public IDeviceFiles DeviceFiles { get; } = files;
    public event Action? Changed;
    public bool Busy { get; private set; }
    public bool IsActive { get; set; } = true;
    public string? Error { get; private set; }
    public string? Notice { get; private set; }
    public Func<Task<bool>>? BackHandler { get; set; }
    public async Task BackAsync()
    {
        if(Busy)return;
        if(BackHandler is not null && await BackHandler())return;
        if(Connected && Page!="Chat")await NavigateAsync("Chat");
    }
    public bool Initialized { get; private set; }
    public string Page { get; private set; } = "Setup";
    public string ServerUrl { get; set; } = AtlasApi.DefaultUrl;
    public bool Connected => Repo.Connected;
    public void Notify()=>Changed?.Invoke();
    public async Task<bool> Run(Func<Task> action)
    {
        if(Busy)return false;
        Busy=true;Error=null;Notice=null;Notify();
        try{await action();return true;}
        catch(Exception e){Error=AtlasRepository.Friendly(e);return false;}
        finally{Busy=false;Notify();}
    }
    public async Task InitializeAsync()
    {
        if(Initialized)return;Initialized=true;Repo.Changed+=Notify;
        await Run(async()=>
        {
            var saved=await credentials.LoadAsync();
            if(saved is null)return;
            ServerUrl=saved.Url;await Repo.ConnectAsync(saved.Url,saved.Token);Page="Chat";
            if(!Repo.Offline)await Repo.HistoryAsync();
        });
    }
    public Task<bool> ConnectAsync(string token,bool remember)=>Run(async()=>
    {
        await Repo.ConnectAsync(ServerUrl,token);
        ServerUrl=Repo.Url;
        if(remember)await credentials.SaveAsync(new Credentials(ServerUrl,token.Trim()));else credentials.Clear();
        Page="Chat";
        if(!Repo.Offline)await Repo.HistoryAsync();
    });
    public Task<bool> NavigateAsync(string page)=>Run(async()=>
    {
        Page=page;
        if(page=="Conversations")await Repo.RefreshConversationsAsync();
        if(page=="Memory")await Repo.RefreshMemoryAsync();
    });
    public void Success(string text){Notice=text;Notify();}
    public void Disconnect()
    {
        if(Busy)return;
        credentials.Clear();Repo.Disconnect();Page="Setup";Error=null;Notice=null;Notify();
    }
}
