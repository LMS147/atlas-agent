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

// One delegated listener for composers created by Blazor; no per-render handlers.
export function observeLayout() {
    const root=document.documentElement;
    const viewport=window.visualViewport;
    let navObserver, observedNav;
    function resizeComposer(target) {
        if(!(target instanceof HTMLTextAreaElement)||!target.matches('[data-autosize]'))return;
        target.style.height='auto';
        target.style.height=Math.min(160,Math.max(48,target.scrollHeight))+'px';
    }
    function update() {
        const nav=document.querySelector('.bottom-navigation');
        if(nav!==observedNav){navObserver?.disconnect();observedNav=nav;if(nav){navObserver=new ResizeObserver(update);navObserver.observe(nav);}}
        if(nav)root.style.setProperty('--nav-inset',Math.ceil(nav.getBoundingClientRect().height)+'px');
        const offset=viewport?Math.max(0,innerHeight-viewport.height-viewport.offsetTop):0;
        root.style.setProperty('--keyboard-offset',offset+'px');
        document.querySelectorAll('[data-autosize]').forEach(resizeComposer);
    }
    const input=e=>resizeComposer(e.target);
    const mutation=new MutationObserver(update);
    mutation.observe(document.getElementById('app')??document.body,{childList:true,subtree:true});
    document.addEventListener('input',input);
    viewport?.addEventListener('resize',update);viewport?.addEventListener('scroll',update);
    window.addEventListener('resize',update);update();
    return {dispose(){mutation.disconnect();navObserver?.disconnect();document.removeEventListener('input',input);viewport?.removeEventListener('resize',update);viewport?.removeEventListener('scroll',update);window.removeEventListener('resize',update);root.style.removeProperty('--nav-inset');root.style.removeProperty('--keyboard-offset');}};
}
