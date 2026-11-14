import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const source=await readFile(new URL('../Atlas.UI/wwwroot/atlas-orb.js',import.meta.url),'utf8');
const {buildAtlasOrb,createAtlasOrb}=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
function fixture({reduced=false,quality,compact=false,cost=0}={}) {
    let next=0,now=0,draws=0;const frames=new Map(),events=new Map(),canvasEvents=new Map();let resize,intersection,motion;
    const context={setTransform(){},createRadialGradient:()=>({addColorStop(){}}),fillRect(){draws++;},drawImage(){draws++;},beginPath(){},arc(){},fill(){},stroke(){},moveTo(){},lineTo(){}};
    const canvas={getContext:()=>context,addEventListener:(e,f)=>canvasEvents.set(e,f),removeEventListener:e=>canvasEvents.delete(e)};
    const document={hidden:false,createElement:()=>({getContext:()=>context}),addEventListener:(e,f)=>events.set(e,f),removeEventListener:e=>events.delete(e)};
    const media={matches:reduced,addEventListener:(_,f)=>{motion=f;},removeEventListener(){motion=null;}};
    const host={document,navigator:{hardwareConcurrency:8,deviceMemory:8},devicePixelRatio:3,performance:{now:()=>{now+=cost;return now;}},matchMedia:()=>media,
        requestAnimationFrame:f=>{frames.set(++next,f);return next;},cancelAnimationFrame:n=>frames.delete(n),
        ResizeObserver:class{observe(f){resize=()=>{};}disconnect(){resize=null;}},
        IntersectionObserver:class{observe(){intersection=e=>{};}constructor(f){intersection=f;}disconnect(){intersection=null;}}
    };
    // Capture callback without overwriting it in observe().
    host.IntersectionObserver=class{constructor(f){intersection=f;}observe(){}disconnect(){intersection=null;}};
    const stage={dataset:{},getBoundingClientRect:()=>({width:360,height:320})};
    let failures=0;const orb=buildAtlasOrb(canvas,stage,{host,quality,compact,onFailure:()=>failures++});
    function advance(seconds=1,fps=60){for(let i=0;i<seconds*fps;i++){now+=1000/fps;const batch=[...frames.values()];frames.clear();batch.forEach(f=>f(now));assert.ok(frames.size<=1,'only one animation callback');}}
    return {orb,canvas,stage,media,frames,events,canvasEvents,advance,document,host,get failures(){return failures;},get draws(){return draws;},hide(value){intersection([{isIntersecting:!value}]);},motion:()=>motion?.()};
}

test('time-based orbit speed is similar across frame rates and remains three-dimensional',()=>{
    const a=fixture(),b=fixture();a.advance(8,60);b.advance(8,120);
    assert.ok(Math.abs(a.orb.getDiagnostics().orbitTime-b.orb.getDiagnostics().orbitTime)<.04);
    assert.ok(a.draws>1000);assert.equal(a.stage.dataset.orbReady,'true');
    a.orb.dispose();b.orb.dispose();
});
test('idle, thinking, speaking, disconnected and error transition without duplicate loops',()=>{
    const f=fixture();f.advance(1);const idle=f.orb.getDiagnostics().orbitTime;
    f.orb.setState('thinking');f.advance(4);assert.ok(f.orb.getDiagnostics().orbitTime-idle>1.3);
    for(const state of ['speaking','disconnected','error','idle']){f.orb.setState(state,true);f.advance(1);assert.equal(f.orb.getDiagnostics().state,state);}
    f.orb.setState('unknown');assert.equal(f.orb.getDiagnostics().state,'idle');f.orb.dispose();
});
test('navigation, offscreen, background, resume and disposal release the animation loop',()=>{
    const f=fixture();f.advance();f.orb.setState('idle',false);const before=f.orb.getDiagnostics().frames;
    f.advance(2);assert.equal(f.orb.getDiagnostics().frames,before);assert.equal(f.frames.size,0);
    f.orb.setState('idle',true);f.advance();assert.ok(f.orb.getDiagnostics().frames>before);
    f.document.hidden=true;f.events.get('visibilitychange')();assert.equal(f.frames.size,0);
    f.document.hidden=false;f.events.get('visibilitychange')();f.advance();
    f.hide(true);assert.equal(f.frames.size,0);f.hide(false);f.advance();
    f.orb.dispose();f.orb.dispose();assert.equal(f.frames.size,0);assert.equal(f.events.size,0);assert.equal(f.canvasEvents.size,0);
    assert.equal(f.canvas.width,1);assert.equal(f.orb.getDiagnostics().disposed,true);
    f.orb.setState('speaking',true);assert.equal(f.frames.size,0);
});
test('reduced motion is static and stops scheduling after a state settles',()=>{
    const f=fixture({reduced:true});f.advance(2);assert.equal(f.orb.getDiagnostics().orbitTime,0);assert.equal(f.frames.size,0);
    f.orb.setState('thinking');f.advance(5);assert.equal(f.orb.getDiagnostics().orbitTime,0);assert.equal(f.frames.size,0);
    f.media.matches=false;f.motion();f.advance();assert.ok(f.orb.getDiagnostics().orbitTime>0);f.orb.dispose();
});
test('low tier caps resolution and density; sustained slow draws adapt further',()=>{
    const low=fixture({quality:'low'});assert.equal(low.orb.getDiagnostics().particles,1100);assert.equal(low.orb.getDiagnostics().resolution,1.25);low.orb.dispose();
    const slow=fixture({cost:25});slow.advance(5);assert.ok(slow.orb.getDiagnostics().particles<1800);assert.ok(slow.orb.getDiagnostics().resolution<1.75);slow.orb.dispose();
});
test('canvas loss reports once and stops rendering for the matching static fallback',()=>{
    const f=fixture();f.advance();f.canvasEvents.get('contextlost')({preventDefault(){}});
    assert.equal(f.failures,1);assert.equal(f.frames.size,0);assert.equal(f.orb.getDiagnostics().failed,true);
    f.orb.dispose();
});
test('an unavailable Canvas fails before allocating observers or animation loops',()=>{
    assert.throws(()=>buildAtlasOrb({getContext:()=>null},{},{}),/Canvas unavailable/);
});

test('Blazor factory returns callable renderer methods, not a second reference handle',()=>{
    const f=fixture();f.orb.dispose();
    const values={...f.host,DotNet:{createJSObjectReference(){throw new Error('Do not double-wrap a Blazor return value');}}};
    const saved=new Map(Object.keys(values).map(key=>[key,Object.getOwnPropertyDescriptor(globalThis,key)]));
    let renderer;
    try{
        for(const [key,value] of Object.entries(values))Object.defineProperty(globalThis,key,{configurable:true,writable:true,value});
        renderer=createAtlasOrb(f.canvas,f.stage,{invokeMethodAsync:()=>Promise.resolve()},false);
        assert.equal(typeof renderer.setState,'function');assert.equal(typeof renderer.dispose,'function');
        renderer.setState('thinking',false);assert.equal(renderer.getDiagnostics().state,'thinking');
    }finally{
        renderer?.dispose();
        for(const [key,descriptor] of saved){if(descriptor)Object.defineProperty(globalThis,key,descriptor);else delete globalThis[key];}
    }
});
