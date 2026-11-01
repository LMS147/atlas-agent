using Microsoft.Data.Sqlite;
using System.Text.Json;
namespace Atlas.Core;

/// <summary>Separate MAUI cache. Workspace hashes isolate servers and credentials.</summary>
public sealed class CacheStore
{
    private readonly string connectionString;
    public CacheStore(string path)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(path))!);
        connectionString = new SqliteConnectionStringBuilder { DataSource = path }.ToString();
        using var db = Open();
        using var cmd = db.CreateCommand();
        cmd.CommandText = "CREATE TABLE IF NOT EXISTS documents(scope TEXT NOT NULL,kind TEXT NOT NULL,id TEXT NOT NULL,json TEXT NOT NULL,PRIMARY KEY(scope,kind,id));";
        cmd.ExecuteNonQuery();
    }
    private SqliteConnection Open() { var db = new SqliteConnection(connectionString); db.Open(); return db; }
    public List<T> All<T>(string scope, string kind)
    {
        using var db = Open(); using var cmd = db.CreateCommand();
        cmd.CommandText = "SELECT json FROM documents WHERE scope=$scope AND kind=$kind";
        cmd.Parameters.AddWithValue("$scope", scope); cmd.Parameters.AddWithValue("$kind", kind);
        using var reader = cmd.ExecuteReader(); var rows = new List<T>();
        while (reader.Read()) rows.Add(JsonSerializer.Deserialize<T>(reader.GetString(0), AtlasApi.Json)!);
        return rows;
    }
    public void Put<T>(string scope, string kind, string id, T item) => PutBatch(scope, kind, [(id,item)]);
    public void PutBatch<T>(string scope, string kind, IEnumerable<(string Id,T Item)> items)
    {
        using var db = Open(); using var tx = db.BeginTransaction();
        foreach (var (id,item) in items)
        {
            using var cmd = db.CreateCommand(); cmd.Transaction = tx;
            cmd.CommandText = "INSERT OR REPLACE INTO documents(scope,kind,id,json) VALUES($scope,$kind,$id,$json)";
            cmd.Parameters.AddWithValue("$scope", scope); cmd.Parameters.AddWithValue("$kind", kind);
            cmd.Parameters.AddWithValue("$id", id); cmd.Parameters.AddWithValue("$json", JsonSerializer.Serialize(item, AtlasApi.Json));
            cmd.ExecuteNonQuery();
        }
        tx.Commit();
    }
    public void Delete(string scope, string kind, string? id = null)
    {
        using var db = Open(); using var cmd = db.CreateCommand();
        cmd.CommandText = "DELETE FROM documents WHERE scope=$scope AND kind=$kind" + (id is null ? "" : " AND id=$id");
        cmd.Parameters.AddWithValue("$scope",scope);cmd.Parameters.AddWithValue("$kind",kind);
        if(id is not null)cmd.Parameters.AddWithValue("$id",id);
        cmd.ExecuteNonQuery();
    }
}
