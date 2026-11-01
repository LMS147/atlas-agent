using System.Text.Json;
using Atlas.Core;
namespace Atlas.Mobile;
public sealed class DeviceCredentials : ICredentialStore
{
    private const string Key="atlas.connection.v1";
    public async Task<Credentials?> LoadAsync()
    {
        try{var text=await SecureStorage.Default.GetAsync(Key);return text is null?null:JsonSerializer.Deserialize<Credentials>(text);}
        catch{SecureStorage.Default.Remove(Key);throw new InvalidOperationException("Saved credentials could not be restored. Enter the server and token again.");}
    }
    public Task SaveAsync(Credentials value)=>SecureStorage.Default.SetAsync(Key,JsonSerializer.Serialize(value));
    public void Clear()=>SecureStorage.Default.Remove(Key);
}
