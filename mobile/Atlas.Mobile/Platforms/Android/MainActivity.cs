using Android.App;
using Android.Content.PM;
namespace Atlas.Mobile;
[Activity(Theme="@style/Maui.SplashTheme",MainLauncher=true,WindowSoftInputMode=Android.Views.SoftInput.AdjustResize,LaunchMode=LaunchMode.SingleTop,ConfigurationChanges=ConfigChanges.ScreenSize|ConfigChanges.Orientation|ConfigChanges.UiMode|ConfigChanges.ScreenLayout|ConfigChanges.SmallestScreenSize|ConfigChanges.Density)]
public class MainActivity : MauiAppCompatActivity { }
