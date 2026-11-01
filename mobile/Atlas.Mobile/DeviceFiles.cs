using Atlas.Core;
namespace Atlas.Mobile;
public sealed class DeviceFiles : IDeviceFiles
{
    public async Task<(string Name,byte[] Content)?> PickAsync()
    {
        var file=await FilePicker.Default.PickAsync(new PickOptions{PickerTitle="Upload a file to Atlas (5 MiB maximum)"});
        if(file is null)return null;
        await using var stream=await file.OpenReadAsync();
        return(file.FileName,await AtlasApi.ReadBoundedAsync(stream));
    }
    public async Task SaveAsync(string name,byte[] content)
    {
        // The native share sheet provides save/open destinations without broad storage access.
        var folder=Path.Combine(FileSystem.CacheDirectory,"atlas-downloads",Guid.NewGuid().ToString("N"));Directory.CreateDirectory(folder);
        var path=Path.Combine(folder,Path.GetFileName(name));await File.WriteAllBytesAsync(path,content);
        await Share.Default.RequestAsync(new ShareFileRequest{Title="Save or open Atlas file",File=new ShareFile(path)});
    }
    public Task<bool> ConfirmAsync(string title,string message)=>MainThread.InvokeOnMainThreadAsync(async()=>
    {
        var page=Application.Current?.Windows.FirstOrDefault()?.Page ?? throw new InvalidOperationException("No active app window.");
        return await page.DisplayAlertAsync(title,message,"Confirm","Cancel");
    });
}
