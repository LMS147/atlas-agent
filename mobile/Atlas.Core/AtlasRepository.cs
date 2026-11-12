using System.Security.Cryptography;
using System.Text;
namespace Atlas.Core;

public sealed class AtlasRepository(CacheStore cache, Func<string,string,AtlasApi>? factory = null) : IDisposable
{
    private AtlasApi? api;
    public bool StreamingChat { get; private set; }
    public string StreamText { get; private set; } = "";
    public string StreamPhase { get; private set; } = "";
    public event Action? Changed;
    private readonly SemaphoreSlim chatGate = new(1,1);
    public string Scope { get; private set; } = "";
    public string Url => api?.Url ?? AtlasApi.DefaultUrl;
    public string ConversationId { get; private set; } = "";
    public bool Connected => api is not null;
    public bool Offline { get; private set; }
    public List<Conversation> Conversations => cache.All<Conversation>(Scope,"conversations").OrderByDescending(x=>x.UpdatedAt).ToList();
    public Conversation? Current => Conversations.FirstOrDefault(x=>x.Id==ConversationId);
    public List<LocalMessage> Messages => cache.All<LocalMessage>(Scope,"messages").Where(x=>x.ConversationId==ConversationId).OrderBy(x=>x.CreatedAt).ThenBy(x=>x.Role=="user"?0:1).ToList();
    public List<MemoryItem> Memories => cache.All<MemoryItem>(Scope,"memory");
    private AtlasApi Api => api ?? throw new InvalidOperationException("Connect your Atlas server first.");
    private Task<T> Get<T>(string path) => Api.JsonAsync<T>(HttpMethod.Get,path);
    public async Task ConnectAsync(string url,string token)
    {
        await chatGate.WaitAsync();
        AtlasApi? candidate=null;
        try
        {
            candidate=factory?.Invoke(url,token) ?? new AtlasApi(url,token);
            var scope=Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(candidate.Url+"\n"+token.Trim())));
            var previous=cache.All<Conversation>(scope,"conversations");
            List<Conversation>? rows=null; var offline=false; var streaming=false;
            try
            {
                var health=await candidate.JsonAsync<Health>(HttpMethod.Get,"health");
                streaming=health.StreamingChat;
                if(health.Status!="ok")throw new IOException("Atlas is not ready.");
                rows=await candidate.JsonAsync<List<Conversation>>(HttpMethod.Get,"conversations?include_deleted=true");
                if(!rows.Any(x=>!x.Deleted) && previous.Count==0)
                    rows.Add(await candidate.JsonAsync<Conversation>(HttpMethod.Post,"conversations",new {title="New chat"}));
            }
            catch(Exception e) when(e is HttpRequestException or OperationCanceledException)
            {
                if(previous.Count==0)throw;
                offline=true;
            }
            api?.Dispose();api=candidate;candidate=null;Scope=scope;Offline=offline;StreamingChat=streaming;
            if(rows is not null)Sync(rows);
            foreach(var msg in cache.All<LocalMessage>(Scope,"messages").Where(x=>x.Delivery==Delivery.Pending))
                cache.Put(Scope,"messages",msg.Id,msg with { Delivery=Delivery.Recoverable,Error="App interrupted. Check for the existing reply." });
            SelectDefault();
        }
        finally {candidate?.Dispose();chatGate.Release();}
    }
    private void Sync(List<Conversation> rows)
    {
        var previous=Conversations;
        foreach(var old in previous.Where(x=>!rows.Any(r=>r.Id==x.Id)))cache.Put(Scope,"conversations",old.Id,old with {ServerAvailable=false});
        foreach(var row in rows)
        {
            if(row.Deleted){RemoveCache(row.Id);continue;}
            var old=previous.FirstOrDefault(x=>x.Id==row.Id);
            cache.Put(Scope,"conversations",row.Id,row with {ServerAvailable=true,BeforeCursor=old?.BeforeCursor,HasMore=old?.HasMore??false});
        }
    }
    private void SelectDefault()
    {
        var saved=cache.All<Selection>(Scope,"selection").FirstOrDefault()?.Id;
        ConversationId=Conversations.FirstOrDefault(x=>x.Id==saved)?.Id ?? Conversations.FirstOrDefault()?.Id ?? "";
        cache.Put(Scope,"selection","current",new Selection(ConversationId));
    }
    public void Select(string id)
    {
        if(!Conversations.Any(x=>x.Id==id))throw new ArgumentException("Conversation is not in this workspace.");
        ConversationId=id;cache.Put(Scope,"selection","current",new Selection(id));
    }
    public async Task RefreshConversationsAsync(){Sync(await Get<List<Conversation>>("conversations?include_deleted=true"));Offline=false;SelectDefault();}
    public async Task NewConversationAsync(string title="New chat")
    {
        title=Title(title);
        var row=await Api.JsonAsync<Conversation>(HttpMethod.Post,"conversations",new {title});
        cache.Put(Scope,"conversations",row.Id,row);Select(row.Id);Offline=false;
    }
    public async Task RenameAsync(string id,string title)
    {
        title=Title(title);var row=await Api.JsonAsync<Conversation>(HttpMethod.Patch,$"conversations/{id}",new {title});
        var old=Conversations.FirstOrDefault(x=>x.Id==id);
        cache.Put(Scope,"conversations",id,row with{BeforeCursor=old?.BeforeCursor,HasMore=old?.HasMore??false});
    }
    private static string Title(string value){value=value.Trim();if(value.Length is <1 or >80)throw new ArgumentException("Titles must contain 1–80 characters.");return value;}
    public async Task DeleteConversationAsync(string id)
    {
        if(Conversations.First(x=>x.Id==id).ServerAvailable)await Api.EmptyAsync(HttpMethod.Delete,$"conversations/{id}");
        RemoveCache(id);SelectDefault();
    }
    private void RemoveCache(string id)
    {
        cache.Delete(Scope,"conversations",id);
        foreach(var msg in cache.All<LocalMessage>(Scope,"messages").Where(x=>x.ConversationId==id))cache.Delete(Scope,"messages",msg.Id);
    }
    public void ClearLocalChat(){foreach(var msg in Messages)cache.Delete(Scope,"messages",msg.Id);}
    public async Task HistoryAsync(bool earlier=false)
    {
        var current=Current;
        if(current is null || !current.ServerAvailable || (earlier && !current.HasMore))return;
        var path=$"conversations/{current.Id}/messages?limit=50"+(earlier?$"&before={current.BeforeCursor}":"");
        var page=await Get<MessagePage>(path);var local=Messages;
        var rows=page.Items.Select(item=>
        {
            var existing=local.FirstOrDefault(x=>x.RequestId==item.RequestId && x.Role==item.Role);
            return new LocalMessage(existing?.Id??item.RequestId+"-"+item.Role,current.Id,item.RequestId,item.Role,item.Text,item.CreatedAt);
        });
        cache.PutBatch(Scope,"messages",rows.Select(x=>(x.Id,x)));
        cache.Put(Scope,"conversations",current.Id,current with{BeforeCursor=page.NextBefore,HasMore=page.HasMore});Offline=false;
    }
    public async Task SendAsync(string text)
    {
        await chatGate.WaitAsync();
        try
        {
            text=text.Trim();if(text.Length is <1 or >8000)throw new ArgumentException("Messages must contain 1–8,000 characters.");
            if(Current is null || !Current.ServerAvailable)throw new ArgumentException("Create an available server conversation first.");
            if(Messages.Any(x=>x.Role=="user" && x.Delivery is Delivery.Pending or Delivery.Recoverable or Delivery.NotReceived))throw new ArgumentException("Resolve the previous delivery before sending another message.");
            var id=Guid.NewGuid().ToString();var msg=new LocalMessage(id+"-user",ConversationId,id,"user",text,DateTimeOffset.UtcNow.ToUnixTimeMilliseconds(),Delivery.Pending);
            cache.Put(Scope,"messages",msg.Id,msg);Changed?.Invoke(); // Durable before any inference.
            await Deliver(msg);
        }
        finally{chatGate.Release();}
    }
    public async Task RetryAsync(string id,bool fresh)
    {
        await chatGate.WaitAsync();
        try
        {
            var msg=Messages.First(x=>x.Id==id && x.Role=="user");
            if(fresh && msg.Delivery!=Delivery.Failed || !fresh && msg.Delivery is not (Delivery.Recoverable or Delivery.NotReceived))throw new ArgumentException("Check the existing request before retrying.");
            if(Current?.ServerAvailable!=true)throw new ArgumentException("Conversation unavailable. Refresh the server list.");
            msg=msg with{RequestId=fresh?Guid.NewGuid().ToString():msg.RequestId,Delivery=Delivery.Pending,Error=null};
            cache.Put(Scope,"messages",msg.Id,msg);await Deliver(msg);
        }
        finally{chatGate.Release();}
    }
    private async Task Deliver(LocalMessage msg)
    {
        try
        {
            var body=new {message=msg.Text,conversation_id=msg.ConversationId,request_id=msg.RequestId,require_existing=true};
            string reply;
            if(StreamingChat)
                reply=await Api.StreamChatAsync(body,msg.RequestId,(phase,text)=>{StreamPhase=phase;StreamText=text;Changed?.Invoke();});
            else reply=(await Api.JsonAsync<Reply>(HttpMethod.Post,"chat",body)).ReplyText;
            if(string.IsNullOrWhiteSpace(reply))throw new IOException("Atlas returned an invalid reply. Check for the saved reply.");
            Complete(msg,reply);Offline=false;
        }
        catch(Exception error)
        {
            var state=error is AtlasApiException e && e.Status is 401 or 403 or 404 or 410 or 422 or 429 or 502 or 504 ? Delivery.Failed : Delivery.Recoverable;
            cache.Put(Scope,"messages",msg.Id,msg with{Delivery=state,Error=Friendly(error)});throw;
        }
        finally{StreamText="";StreamPhase="";Changed?.Invoke();}
        await UpdateSummary(msg.ConversationId);
    }
    public async Task RecoverAsync(string id)
    {
        await chatGate.WaitAsync();
        try
        {
            var msg=Messages.First(x=>x.Id==id && x.Role=="user");
            if(msg.Delivery is not (Delivery.Recoverable or Delivery.NotReceived))throw new ArgumentException("This message does not need recovery.");
            try
            {
                var status=await Get<RequestStatus>($"conversations/{msg.ConversationId}/requests/{msg.RequestId}");
                if(status.RequestId!=msg.RequestId)throw new IOException("Request status did not match this message.");
                switch(status.Status)
                {
                    case "done" when !string.IsNullOrWhiteSpace(status.Reply):Complete(msg,status.Reply);await UpdateSummary(msg.ConversationId);break;
                    case "pending":cache.Put(Scope,"messages",msg.Id,msg with{Delivery=Delivery.Recoverable,Error="Atlas is still processing. Check again later."});break;
                    case "not_found":cache.Put(Scope,"messages",msg.Id,msg with{Delivery=Delivery.NotReceived,Error="No record was found. Confirm retry delivery with the same request ID."});break;
                    case "failed" or "interrupted":cache.Put(Scope,"messages",msg.Id,msg with{Delivery=Delivery.Failed,Error="The request did not finish. Check memory before confirming a new request."});break;
                    default:throw new IOException("Invalid request status. Check again before sending anything new.");
                }
                Offline=false;
            }
            catch(Exception error)
            {
                var delivery=error is AtlasApiException e && e.Status is 401 or 403 or 404 or 410?Delivery.Failed:Delivery.Recoverable;
                cache.Put(Scope,"messages",msg.Id,msg with{Delivery=delivery,Error=Friendly(error)});throw;
            }
        }
        finally{chatGate.Release();}
    }
    private void Complete(LocalMessage msg,string reply)
    {
        var user=msg with{Delivery=Delivery.Sent,Error=null};
        var assistant=new LocalMessage(msg.RequestId+"-assistant",msg.ConversationId,msg.RequestId,"assistant",reply,Math.Max(DateTimeOffset.UtcNow.ToUnixTimeMilliseconds(),msg.CreatedAt+1));
        cache.PutBatch(Scope,"messages",[(user.Id,user),(assistant.Id,assistant)]);Changed?.Invoke();
    }
    private async Task UpdateSummary(string id)
    {
        try
        {
            var row=await Get<Conversation>($"conversations/{id}");var old=Conversations.FirstOrDefault(x=>x.Id==id);
            cache.Put(Scope,"conversations",id,row with{BeforeCursor=old?.BeforeCursor,HasMore=old?.HasMore??false});
        }
        catch(HttpRequestException){}catch(AtlasApiException){}catch(TaskCanceledException){}
    }
    public async Task RefreshMemoryAsync()
    {
        var rows=await Get<List<MemoryItem>>("memory");cache.Delete(Scope,"memory");cache.PutBatch(Scope,"memory",rows.Select(x=>(x.Id,x)));
    }
    public async Task SaveMemoryAsync(string? id,string section,string fact)
    {
        fact=" ".JoinWords(fact);
        if(fact.Length is <1 or >300)throw new ArgumentException("Facts must contain 1–300 characters.");
        if(id is null)await Api.JsonAsync<MemoryItem>(HttpMethod.Post,"memory",new{section,fact});
        else await Api.EmptyAsync(HttpMethod.Patch,"memory/"+id,new{section,fact});
        await RefreshMemoryAsync();
    }
    public async Task DeleteMemoryAsync(string id){await Api.EmptyAsync(HttpMethod.Delete,"memory/"+id);await RefreshMemoryAsync();}
    public Task<CompactPlan> CompactPreviewAsync()=>Get<CompactPlan>("memory/compact");
    public async Task CompactAsync(string revision){await Api.JsonAsync<CompactPlan>(HttpMethod.Post,"memory/compact",new{revision});await RefreshMemoryAsync();}
    public Task<Profile> ProfileAsync()=>Get<Profile>("agent");
    public Task<List<FileItem>> FilesAsync(string directory)=>Get<List<FileItem>>("files?directory="+Uri.EscapeDataString(directory));
    public Task<FileDocument> DocumentAsync(string path)=>Get<FileDocument>("files/text?path="+Uri.EscapeDataString(path));
    public async Task EditFileAsync(FileDocument file,string text)
    {
        if(!file.Writable || Encoding.UTF8.GetByteCount(text)>256*1024)throw new ArgumentException("Only workspace UTF-8 files up to 256 KiB can be edited.");
        await Api.JsonAsync<FileItem>(HttpMethod.Put,"files/text?path="+Uri.EscapeDataString(file.Path),new{content=text,revision=file.Revision});
    }
    public Task UploadAsync(string name,byte[] bytes)=>Api.UploadAsync(name,bytes);
    public Task<byte[]> DownloadAsync(string path)=>Api.DownloadAsync(path);
    public void Disconnect(){api?.Dispose();api=null;Scope="";ConversationId="";Offline=false;StreamingChat=false;StreamText="";StreamPhase="";}
    public static string Friendly(Exception e)=>e switch
    {
        AtlasApiException or ArgumentException or InvalidOperationException=>e.Message,
        HttpRequestException or OperationCanceledException=>"Connection interrupted. Check the server/tunnel, then check for the existing reply.",
        _=>"Atlas could not complete the operation. Your saved data is retained."
    };
    public void Dispose(){api?.Dispose();chatGate.Dispose();}
    private sealed record Reply([property:System.Text.Json.Serialization.JsonPropertyName("reply")]string ReplyText);
}
internal static class Words {public static string JoinWords(this string separator,string input)=>string.Join(separator,input.Split((char[]?)null,StringSplitOptions.RemoveEmptyEntries));}
