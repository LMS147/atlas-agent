using Microsoft.Extensions.DependencyInjection;
using Atlas.Core;
using Atlas.UI;
namespace Atlas.Mobile;
public static class MauiProgram
{
    public static MauiApp CreateMauiApp()
    {
        var builder=MauiApp.CreateBuilder();
        builder.UseMauiApp<App>();builder.Services.AddMauiBlazorWebView();
#if DEBUG
        builder.Services.AddBlazorWebViewDeveloperTools();
#endif
        builder.Services.AddSingleton(new CacheStore(Path.Combine(FileSystem.AppDataDirectory,"atlas-hybrid.sqlite3")));
        builder.Services.AddSingleton<AtlasRepository>();
        builder.Services.AddSingleton<ICredentialStore,DeviceCredentials>();
        builder.Services.AddSingleton<IDeviceFiles,DeviceFiles>();
        builder.Services.AddSingleton<IAtlasSpeech,DeviceSpeech>();
        builder.Services.AddSingleton<AppState>();builder.Services.AddSingleton<MainPage>();
        return builder.Build();
    }
}
