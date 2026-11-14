// Atlas's procedural presence: 3D-projected points and depth-split curved orbits,
// rasterized with Canvas 2D. No WebGL, textures, network, camera or microphone.
const TAU = Math.PI * 2;
export const STATES = Object.freeze({
    idle:         {speed:.19, glow:.72, spread:1},
    listening:    {speed:.25, glow:.88, spread:1.07}, // only for real capture hosts
    thinking:     {speed:.52, glow:.96, spread:1.02},
    speaking:     {speed:.26, glow:.90, spread:1.03},
    disconnected: {speed:.09, glow:.34, spread:.98},
    error:        {speed:.14, glow:.58, spread:1}
});

export function createAtlasOrb(canvas, stage, receiver, compact=false) {
    return DotNet.createJSObjectReference(buildAtlasOrb(canvas, stage, {
        compact, active:false, onFailure:()=>receiver.invokeMethodAsync('RendererFailed').catch(()=>{})
    }));
}

export function buildAtlasOrb(canvas, stage, options={}) {
    const context=canvas.getContext('2d',{alpha:false});
    if(!context)throw new Error('Canvas unavailable');
    const host=options.host??globalThis;
    const media=host.matchMedia('(prefers-reduced-motion: reduce)');
    const cores=host.navigator?.hardwareConcurrency??4, memory=host.navigator?.deviceMemory??4;
    const low=options.quality==='low'||cores<=4||memory<=2;
    const quality=low?'low':'standard';
    const count=options.compact?(low?350:700):(low?1100:1800);
    let density=count, resolution=Math.min(host.devicePixelRatio||1,low?1.25:1.75);
    let seed=147;
    const random=()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed/4294967296;};
    const points=Array.from({length:count},()=>{
        const y=random()*2-1, angle=random()*TAU, ring=Math.sqrt(1-y*y);
        const radius=.95+random()*.07;
        return {x:Math.cos(angle)*ring*radius,y:y*radius,z:Math.sin(angle)*ring*radius,
            phase:random()*TAU,size:.55+random()*.85,brightness:.38+random()*.62};
    });
    const dust=Array.from({length:low?40:75},()=>{
        const y=random()*2-1,angle=random()*TAU,r=1.16+random()*.52,ring=Math.sqrt(1-y*y);
        return {x:Math.cos(angle)*ring*r,y:y*r,z:Math.sin(angle)*ring*r,phase:random()*TAU};
    });
    const paths=[
        {rx:1.52,ry:1.22,tilt:.37,turn:.35,phase:.2,speed:1.12},
        {rx:1.38,ry:1.56,tilt:1.12,turn:1.2,phase:2.4,speed:-.86},
        {rx:1.60,ry:1.28,tilt:2.18,turn:.66,phase:4.6,speed:.71},
        {rx:1.30,ry:1.49,tilt:.79,turn:2.21,phase:1.4,speed:-1.04},
        {rx:1.51,ry:1.34,tilt:2.65,turn:1.78,phase:3.2,speed:.93}
    ];
    let width=0,height=0,scale=1,disposed=false,failed=false,active=options.active??true,intersecting=true;
    let frame=0,last=0,elapsed=0,orbitTime=0,frames=0,slowFrames=0;
    let state='idle',speed=STATES.idle.speed,glow=STATES.idle.glow,spread=1,amplitude=null,errorAt=-100;
    const sprites=[];
    function sprite(color){
        const image=host.document.createElement('canvas');image.width=image.height=64;
        const c=image.getContext('2d');if(!c)throw new Error('Canvas unavailable');
        const gradient=c.createRadialGradient(32,32,0,32,32,32);
        gradient.addColorStop(0,'#ffffff');gradient.addColorStop(.09,'#e7ffff');
        gradient.addColorStop(.22,color);gradient.addColorStop(.48,'#0879ef65');gradient.addColorStop(1,'#005bff00');
        c.fillStyle=gradient;c.fillRect(0,0,64,64);sprites.push(image);return image;
    }
    const light=sprite('#76efff'),smallLight=sprite('#238dff');
    function project(x,y,z){const p=4.8/(4.8-z);return {x:width/2+x*scale*p,y:height/2-y*scale*p,z,p};}
    function rotate(point,angle){const c=Math.cos(angle),s=Math.sin(angle);return {x:point.x*c+point.z*s,y:point.y,z:point.z*c-point.x*s};}
    function orbit(path,a,t){
        // Curves gently deform and precess independently, rather than rigid rings.
        const wobble=.055*Math.sin(a*3+t*.31+path.phase);
        const x=(path.rx+wobble)*Math.cos(a),y=(path.ry+wobble)*Math.sin(a);
        const tilt=path.tilt+.055*Math.sin(t*.09+path.phase),turn=path.turn+.045*Math.sin(t*.07+path.phase);
        const xx=x,yy=y*Math.cos(tilt),zz=y*Math.sin(tilt);
        return project((xx*Math.cos(turn)+zz*Math.sin(turn))*spread, yy*spread,(zz*Math.cos(turn)-xx*Math.sin(turn))*spread);
    }
    function dot(point,size,alpha,image=light){
        context.globalAlpha=Math.max(0,Math.min(1,alpha));
        const diameter=size*point.p;
        context.drawImage(image,point.x-diameter/2,point.y-diameter/2,diameter,diameter);
    }
    function draw(){
        context.globalAlpha=1;context.fillStyle='#060c16';context.fillRect(0,0,width,height);
        if(!width||!height)return;
        const reduced=media.matches;
        const breath=reduced?1:1+.025*Math.sin(elapsed*.85);
        const pulse=state==='speaking'?(amplitude===null?.05+.035*Math.sin(elapsed*3.7):Math.min(.15,amplitude*.15)):
            state==='listening'?.025*(1+Math.sin(elapsed*2)):0;
        const energy=glow*breath*(1+pulse);
        const cameraRotation=elapsed*.045;
        // Back halves are drawn first. The near-black core occludes rear paths.
        function trails(front){
            context.lineWidth=options.compact?.65:.85;
            paths.forEach((path,index)=>{
                context.beginPath();let started=false;
                for(let i=0;i<=100;i++){
                    const p=orbit(path,i/100*TAU,elapsed);
                    if((p.z>=0)!==front){started=false;continue;}
                    if(!started){context.moveTo(p.x,p.y);started=true;}else context.lineTo(p.x,p.y);
                }
                context.globalAlpha=energy*(front?.68:.28);context.strokeStyle=index%2?'#338fff':'#086bff';context.stroke();
                for(let node=0;node<2;node++){
                    const angle=orbitTime*path.speed+path.phase+node*2.71;
                    for(let tail=16;tail>=0;tail--){
                        const p=orbit(path,angle-tail*.017*Math.sign(path.speed),elapsed);
                        if((p.z>=0)!==front)continue;
                        dot(p,(tail===0?14:7)*(options.compact?.78:1),energy*(tail===0?.95:.35*Math.pow(1-tail/17,2)),tail===0?light:smallLight);
                        if(tail===0){context.globalAlpha=Math.min(1,energy*1.6);context.fillStyle='#ecffff';context.beginPath();context.arc(p.x,p.y,(options.compact?1.1:1.7)*p.p,0,TAU);context.fill();}
                    }
                }
            });
        }
        trails(false);
        // Occlusion is deliberately dark, never a solid luminous ball.
        context.globalAlpha=.96;context.fillStyle='#060c16';context.beginPath();context.arc(width/2,height/2,scale*.995*spread,0,TAU);context.fill();
        for(let i=0;i<density;i++){
            const source=points[i],p3=rotate(source,cameraRotation);
            const jitter=reduced?0:.009*Math.sin(elapsed*.6+source.phase);
            const p=project(p3.x*(spread+jitter),p3.y*(spread+jitter),p3.z*(spread+jitter));
            const radial=Math.min(1,Math.hypot(p.x-width/2,p.y-height/2)/(scale*spread));
            const shellLight=(.04+1.6*Math.pow(radial,3.8))*(p3.z<0?.22:1);
            context.globalAlpha=Math.min(1,energy*source.brightness*shellLight*(1+pulse));
            context.fillStyle=i%23===0?'#c2faff':i%4===0?'#29c3ff':'#1674ff';
            const size=source.size*p.p*(options.compact?.85:1);
            context.fillRect(p.x,p.y,size,size);
        }
        dust.forEach((source,i)=>{
            const p3=rotate(source,-cameraRotation*.7),p=project(p3.x,p3.y,p3.z);
            const a=media.matches?.14:.12+.09*Math.sin(elapsed*.45+source.phase);
            context.globalAlpha=Math.max(0,a*glow);context.fillStyle='#35b9ff';context.fillRect(p.x,p.y,i%6===0?1.3:.7,i%6===0?1.3:.7);
        });
        trails(true);
        // One quiet indication on error entry; no repeating red flashing.
        const errorAge=elapsed-errorAt;
        if(errorAge>=0&&errorAge<1.5){
            context.globalAlpha=.16*Math.sin(Math.PI*errorAge/1.5);context.strokeStyle='#f0b1b8';context.lineWidth=1;
            context.beginPath();context.arc(width/2,height/2,scale*1.08,0,TAU);context.stroke();
        }
        context.globalAlpha=1;frames++;
    }
    function canRun(){return !disposed&&!failed&&active&&intersecting&&!host.document.hidden&&width>0&&height>0;}
    function cancel(){if(frame)host.cancelAnimationFrame(frame);frame=0;last=0;}
    function fail(){if(disposed||failed)return;failed=true;cancel();stage.dataset.orbReady='false';options.onFailure?.();}
    function tick(now){
        frame=0;if(!canRun())return;
        const interval=media.matches?1000/12:1000/(low?24:30);
        if(last&&now-last<interval){frame=host.requestAnimationFrame(tick);return;}
        const dt=last?Math.min(.1,(now-last)/1000):0;last=now;
        const target=STATES[state];const blend=1-Math.exp(-dt*3);
        speed+=(target.speed-speed)*blend;glow+=(target.glow-glow)*blend;spread+=(target.spread-spread)*blend;
        elapsed+=media.matches?0:dt;orbitTime+=media.matches?0:dt*speed;
        // Error timeout advances even with reduced motion, without animating a flash.
        if(media.matches)errorAt=-100;
        const started=host.performance.now();
        try{draw();}catch{fail();return;}
        if(host.performance.now()-started>18)slowFrames++;else slowFrames=Math.max(0,slowFrames-1);
        if(slowFrames>18){density=Math.max(Math.min(count,320),Math.floor(density*.8));resolution=Math.max(1,resolution-.25);slowFrames=0;resize();}
        if(media.matches&&Math.abs(target.glow-glow)<.003&&Math.abs(target.speed-speed)<.003&&Math.abs(target.spread-spread)<.003)return;
        if(canRun()&&!frame)frame=host.requestAnimationFrame(tick);
    }
    function sync(){if(canRun()){if(!frame){last=0;frame=host.requestAnimationFrame(tick);}}else cancel();}
    function resize(){
        const box=stage.getBoundingClientRect();width=Math.max(0,box.width);height=Math.max(0,box.height);
        scale=Math.min(width,height)*.245;
        canvas.width=Math.max(1,Math.round(width*resolution));canvas.height=Math.max(1,Math.round(height*resolution));
        context.setTransform(resolution,0,0,resolution,0,0);sync();
    }
    const observer=new host.ResizeObserver(resize);
    const intersection=new host.IntersectionObserver(entries=>{intersecting=entries[0]?.isIntersecting??false;sync();});
    const visibility=()=>sync(),motion=()=>{cancel();sync();};
    const contextLost=event=>{event.preventDefault();fail();};
    try{
        observer.observe(stage);intersection.observe(stage);
        host.document.addEventListener('visibilitychange',visibility);media.addEventListener('change',motion);
        canvas.addEventListener('contextlost',contextLost);resize();stage.dataset.orbReady='true';
    }catch(error){observer.disconnect();intersection.disconnect();cancel();throw error;}
    return {
        setState(next,isActive=true,audioAmplitude=null){
            const value=Object.hasOwn(STATES,next)?next:'idle';
            if(value!==state&&value==='error')errorAt=elapsed;
            state=value;active=!!isActive;
            amplitude=state==='speaking'&&Number.isFinite(audioAmplitude)?Math.max(0,Math.min(1,audioAmplitude)):null;
            stage.dataset.orbState=state;sync();
        },
        getDiagnostics(){return {state,active,frames,quality,particles:density,resolution,reducedMotion:media.matches,scheduled:!!frame,disposed,failed,elapsed,orbitTime};},
        dispose(){
            if(disposed)return;disposed=true;cancel();observer.disconnect();intersection.disconnect();
            host.document.removeEventListener('visibilitychange',visibility);media.removeEventListener('change',motion);canvas.removeEventListener('contextlost',contextLost);
            sprites.forEach(image=>{image.width=image.height=1;});canvas.width=canvas.height=1;delete stage.dataset.orbReady;delete stage.dataset.orbState;
        }
    };
}
