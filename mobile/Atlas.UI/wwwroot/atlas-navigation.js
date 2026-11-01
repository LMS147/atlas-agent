let previousFocus, listener;
export function openDrawer(drawer, bridge, openerId) {
    closeDrawer(false);
    previousFocus=document.getElementById(openerId)??document.activeElement;
    const focusable=()=>[...drawer.querySelectorAll('button:not(:disabled),a[href],[tabindex="0"]')].filter(e=>e.getClientRects().length);
    listener=event=>{
        if(event.key==='Escape'){event.preventDefault();bridge.invokeMethodAsync('CloseDrawerFromJS');return;}
        if(event.key!=='Tab')return;
        const nodes=focusable(),first=nodes[0],last=nodes[nodes.length-1];if(!first){event.preventDefault();return;}
        if(event.shiftKey && (document.activeElement===first || !drawer.contains(document.activeElement))){event.preventDefault();last.focus();}
        else if(!event.shiftKey && (document.activeElement===last || !drawer.contains(document.activeElement))){event.preventDefault();first.focus();}
    };
    document.addEventListener('keydown',listener);
    (focusable()[0]??drawer).focus({preventScroll:true});
}
export function closeDrawer(restore=true) {
    if(listener)document.removeEventListener('keydown',listener);
    listener=null;
    if(restore && previousFocus?.isConnected)previousFocus.focus({preventScroll:true});
    if(restore)previousFocus=null;
}
