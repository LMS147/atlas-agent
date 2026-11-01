using Atlas.UI;
using Microsoft.AspNetCore.Components.WebView;
namespace Atlas.Mobile;
public partial class MainPage : ContentPage
{
    private readonly AppState state;
    public MainPage(AppState state){InitializeComponent();this.state=state;}
    protected override bool OnBackButtonPressed()
    {
        if(state.Busy)return true;
        if(state.BackHandler is not null || state.Connected && state.Page!="Chat")
        { _ = state.BackAsync();return true; }
        return base.OnBackButtonPressed();
    }
    private void OnUrlLoading(object? sender,UrlLoadingEventArgs e)
    {
        // Render only bundled UI. Server documents are encoded text, never remote HTML.
        if(e.Url.Host!="0.0.0.1")e.UrlLoadingStrategy=UrlLoadingStrategy.CancelLoad;
    }
}
