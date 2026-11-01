using Atlas.UI;
namespace Atlas.Mobile;
public partial class App : Application
{
    private readonly MainPage page;private readonly AppState state;
    public App(MainPage page,AppState state){InitializeComponent();this.page=page;this.state=state;}
    protected override Window CreateWindow(IActivationState? activationState)
    {
        var window=new Window(page){Title="Atlas"};
        window.Stopped+=(_,_)=>state.IsActive=false;
        window.Deactivated+=(_,_)=>state.IsActive=false;
        window.Resumed+=(_,_)=>state.IsActive=true;
        window.Activated+=(_,_)=>state.IsActive=true;
        window.Destroying+=(_,_)=>state.IsActive=false;
        return window;
    }
}
