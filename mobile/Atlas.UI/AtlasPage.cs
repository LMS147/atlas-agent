using Microsoft.AspNetCore.Components;
namespace Atlas.UI;

/// <summary>Mutable app state must participate in Blazor parameter updates.
/// An injected singleton alone does not invalidate parameterless child components.</summary>
public abstract class AtlasPage : ComponentBase
{
    [CascadingParameter] public AppState State { get; set; } = default!;
}
