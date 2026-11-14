import * as T from './vendor/three/three.module.min.js';

// A small, articulated 3D interpretation of the approved Atlas character.
// It is built from original geometry, not a flat image rotated in a canvas.
export function createAtlas(canvas, container, receiver) {
    return DotNet.createJSObjectReference(buildAtlas(canvas, container, () => receiver.invokeMethodAsync("RendererLost").catch(() => {})));
}
export function buildAtlas(canvas, container, onLost = null) {
    let renderer;
    try {
    renderer = new T.WebGLRenderer({canvas, alpha:true, antialias:true, powerPreference:'low-power'});
    renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5));
    renderer.setClearColor(0x000000,0);
    renderer.outputColorSpace=T.SRGBColorSpace;
    renderer.toneMapping=T.ACESFilmicToneMapping;
    renderer.toneMappingExposure=1.35;
    const scene=new T.Scene();
    const camera=new T.PerspectiveCamera(37,1,.1,30);
    camera.position.set(0,1.55,5.7);camera.lookAt(0,1.45,0);
    scene.add(new T.HemisphereLight(0xc3e8ff,0x17233a,2.6));
    const key=new T.DirectionalLight(0xe2eaff,3.2);key.position.set(-3,5,4);scene.add(key);
    const rim=new T.DirectionalLight(0x227dff,4);rim.position.set(2,3,-3);scene.add(rim);
    const fill=new T.PointLight(0x20cfff,7,8);fill.position.set(-1,2,2);scene.add(fill);
    const mat=(color,roughness=.65,metalness=.15)=>new T.MeshStandardMaterial({color,roughness,metalness});
    const coat=mat(0x11213a,.78,.08), edge=mat(0x1e4e83,.5,.35), black=mat(0x090f19,.36,.3), silver=mat(0x9eaabd,.35,.65), sole=mat(0x273951,.6,.2);
    const glow=new T.MeshBasicMaterial({color:0x42dbff,toneMapped:false});
    const blue=new T.MeshBasicMaterial({color:0x427dff,toneMapped:false});
    const root=new T.Group();scene.add(root);
    const mesh=(parent,geometry,material,x=0,y=0,z=0,scale=null)=>{const m=new T.Mesh(geometry,material);m.position.set(x,y,z);if(scale)m.scale.set(...scale);parent.add(m);return m;};
    const sphere=(p,m,x,y,z,s)=>mesh(p,new T.SphereGeometry(1,32,24),m,x,y,z,s);
    const box=(p,m,x,y,z,s)=>mesh(p,new T.BoxGeometry(...s),m,x,y,z);
    const tube=(p,points,material,radius=.015)=>mesh(p,new T.TubeGeometry(new T.CatmullRomCurve3(points.map(v=>new T.Vector3(...v))),24,radius,7,false),material);
    // Coat, scarf, belt and fitted lower body.
    mesh(root,new T.CylinderGeometry(.36,.57,1.05,40),coat,0,1.22,0);
    const panelL=box(root,coat,-.32,.65,.18,[.27,.9,.17]);panelL.rotation.z=-.1;
    const panelR=box(root,coat,.32,.65,.18,[.27,.9,.17]);panelR.rotation.z=.1;
    tube(root,[[-.32,1.72,.28],[-.25,1.4,.43],[-.27,.8,.43],[-.4,.25,.29]],edge,.018);
    tube(root,[[.32,1.72,.28],[.25,1.4,.43],[.27,.8,.43],[.4,.25,.29]],edge,.018);
    const scarf=mesh(root,new T.TorusGeometry(.32,.12,16,48),black,0,1.73,0);scarf.rotation.x=Math.PI/2;
    const belt=mesh(root,new T.TorusGeometry(.435,.04,8,48),black,0,1.03,0);belt.rotation.x=Math.PI/2;
    box(root,silver,0,1.03,.445,[.15,.105,.035]);box(root,black,.36,.92,.32,[.12,.25,.1]);
    // Atlas chest mark, made from two luminous strokes.
    tube(root,[[-.11,1.39,.465],[0,1.57,.465],[.11,1.39,.465]],glow,.018);
    tube(root,[[-.05,1.45,.468],[.05,1.45,.468]],glow,.013);
    for(const x of [-.21,.21]){
        mesh(root,new T.CapsuleGeometry(.17,.43,8,20),black,x,.57,0);
        mesh(root,new T.CapsuleGeometry(.14,.28,8,20),black,x,.2,.025);
        sphere(root,black,x,-.005,.13,[.185,.1,.31]);
        box(root,sole,x,-.085,.14,[.36,.08,.53]);
        tube(root,[[x-.13,-.04,.36],[x+.13,-.04,.36]],blue,.015);
    }
    function arm(x){
        const joint=new T.Group();joint.position.set(x,1.6,0);root.add(joint);
        mesh(joint,new T.CapsuleGeometry(.145,.37,8,20),coat,0,-.25,0);
        const elbow=new T.Group();elbow.position.set(0,-.55,.03);joint.add(elbow);
        mesh(elbow,new T.CapsuleGeometry(.115,.27,8,20),coat,0,-.16,.03);
        const cuff=mesh(elbow,new T.TorusGeometry(.115,.025,8,24),edge,0,-.32,.03);cuff.rotation.x=Math.PI/2;
        sphere(elbow,black,0,-.43,.04,[.12,.14,.08]);
        for(let i=0;i<4;i++)mesh(elbow,new T.CapsuleGeometry(.022,.085,4,8),black,-.072+i*.046,-.56,.05);
        return {joint,elbow};
    }
    const left=arm(-.49),right=arm(.49);left.joint.rotation.z=-.1;right.joint.rotation.z=.1;
    // Articulated head with a navy hood and silver fringe.
    const head=new T.Group();head.position.set(0,2.08,0);root.add(head);
    const hoodMaterial=coat.clone();hoodMaterial.side=T.DoubleSide;
    mesh(head,new T.SphereGeometry(.69,48,32,Math.PI,Math.PI),hoodMaterial,0,.02,-.04,[1,1.12,.9]);
    const rimHood=mesh(head,new T.TorusGeometry(.58,.065,14,64),coat,0,.03,.13,[1,1.16,1]);
    const rimLine=mesh(head,new T.TorusGeometry(.625,.012,8,64),edge,0,.03,.135,[1,1.16,1]);
    sphere(head,black,0,0,.13,[.48,.53,.355]);
    const eyes=[];
    for(const x of [-.19,.19]){
        const eye=new T.Group();eye.position.set(x,.035,.456);eye.rotation.z=x<0?-.12:.12;head.add(eye);
        sphere(eye,glow,0,0,0,[.123,.067,.025]);
        sphere(eye,blue,0,0,.024,[.033,.052,.011]);
        sphere(eye,black,0,0,.035,[.013,.04,.006]);
        sphere(eye,new T.MeshBasicMaterial({color:0xe7ffff}),-.02,.018,.039,[.012,.014,.005]);
        eyes.push(eye);
        tube(head,[[x-.08,.19,.45],[x,.215,.47],[x+.065,.19,.46]],glow,.012);
        const ear=mesh(head,new T.CylinderGeometry(.15,.15,.095,28),black,Math.sign(x)*.49,.005,.02);ear.rotation.z=Math.PI/2;
        const earLight=mesh(head,new T.TorusGeometry(.12,.013,8,32),blue,Math.sign(x)*.545,.005,.02);earLight.rotation.y=Math.PI/2;
    }
    const mouth=sphere(head,black,0,-.195,.464,[.105,.012,.016]);
    const lip=tube(head,[[-.09,-.19,.473],[0,-.213,.482],[.09,-.19,.473]],edge,.009);
    // Broad, curved silver locks preserve Atlas's side-swept fringe.
    function lock(draw){const shape=new T.Shape();draw(shape);shape.closePath();return mesh(head,new T.ExtrudeGeometry(shape,{depth:.025,bevelEnabled:true,bevelSize:.012,bevelThickness:.012,bevelSegments:3,curveSegments:16}),silver,0,0,.46);}
    lock(s=>{s.moveTo(.27,.47);s.quadraticCurveTo(-.06,.61,-.33,.30);s.quadraticCurveTo(-.18,.38,-.25,.18);s.quadraticCurveTo(.05,.28,.27,.47);});
    lock(s=>{s.moveTo(-.08,.48);s.quadraticCurveTo(-.35,.46,-.40,.19);s.quadraticCurveTo(-.32,.28,-.26,.22);s.quadraticCurveTo(-.25,.39,-.08,.48);});
    lock(s=>{s.moveTo(.23,.48);s.quadraticCurveTo(.43,.40,.43,.18);s.quadraticCurveTo(.35,.24,.35,.12);s.quadraticCurveTo(.29,.31,.23,.48);});
    // Orbital halo follows the head while its satellite revolves independently.
    const halo=new T.Group();halo.position.set(0,.67,0);halo.rotation.z=-.15;halo.rotation.x=.65;head.add(halo);
    const ring=mesh(halo,new T.TorusGeometry(.76,.012,8,80),blue);ring.rotation.x=Math.PI/2;
    const satellite=sphere(halo,glow,.76,0,0,[.047,.047,.047]);
    // Floating light near Atlas, deliberately separate from the speech state.
    const orb=new T.Group();orb.position.set(-.85,1.02,.3);root.add(orb);
    sphere(orb,glow,0,0,0,[.06,.06,.06]);
    for(const angle of [.5,-.5]){const r=mesh(orb,new T.TorusGeometry(.16,.006,6,40),blue);r.rotation.x=1.1;r.rotation.z=angle;}
    let mode='idle',active=true,visible=true,disposed=false,yaw=0,targetYaw=0,waveAt=-99,lastFrame=0,frames=0;
    const started=performance.now(), reduced=matchMedia('(prefers-reduced-motion: reduce)');
    function resize(){const b=container.getBoundingClientRect();renderer.setSize(Math.max(1,b.width),Math.max(1,b.height),false);camera.aspect=b.width/Math.max(1,b.height);camera.updateProjectionMatrix();}
    const observer=new ResizeObserver(resize);observer.observe(container);resize();
    let drag=null;
    const down=e=>{drag={x:e.clientX,yaw:targetYaw};canvas.setPointerCapture(e.pointerId);};
    const move=e=>{if(drag)targetYaw=T.MathUtils.clamp(drag.yaw+(e.clientX-drag.x)*.009,-1.1,1.1);};
    const up=()=>{drag=null;};
    const keydown=e=>{if(e.key==='ArrowLeft'||e.key==='ArrowRight'){e.preventDefault();targetYaw=T.MathUtils.clamp(targetYaw+(e.key==='ArrowLeft'?-.15:.15),-1.1,1.1);}};
    canvas.addEventListener('pointerdown',down);canvas.addEventListener('pointermove',move);canvas.addEventListener('pointerup',up);canvas.addEventListener('pointercancel',up);canvas.addEventListener('keydown',keydown);
    let lost=false;
    const contextLost=e=>{e.preventDefault();lost=true;container.classList.add('webgl-lost');onLost?.();};
    canvas.addEventListener('webglcontextlost',contextLost);
    const intersection=new IntersectionObserver(entries=>{visible=entries[0]?.isIntersecting??true;});intersection.observe(container);
    renderer.setAnimationLoop(now=>{
        if(disposed||lost||!active||!visible||document.hidden||now-lastFrame<1000/30)return;
        lastFrame=now;const t=(now-started)/1000;
        yaw=T.MathUtils.lerp(yaw,targetYaw,.12);root.rotation.y=yaw;
        const motion=reduced.matches?0:1;
        root.position.y=.015+Math.sin(t*1.7)*.018*motion;
        head.rotation.z=Math.sin(t*.7)*.035*motion;
        head.rotation.y=Math.sin(t*.53)*.06*motion;
        head.rotation.x=mode==='thinking'?Math.sin(t*2)*.045*motion:.015*Math.sin(t)*motion;
        const blink=reduced.matches?1:((t%4.7)>.14?1:Math.max(.07,Math.abs((t%4.7)-.07)/.07));
        eyes.forEach(e=>e.scale.y=blink);
        const talking=mode==='speaking';
        const open=talking?(.3+Math.abs(Math.sin(t*13)*Math.sin(t*5.2))):0;
        mouth.scale.y=.012+open*.10;lip.position.y=-open*.025;
        const spin=t*(mode==='thinking'?2.3:.55)*motion;
        satellite.position.set(Math.cos(spin)*.76,0,Math.sin(spin)*.76);
        orb.rotation.y=t*.8*motion;orb.position.y=1.02+Math.sin(t*1.4)*.045*motion;
        const wave=t-waveAt;
        left.joint.rotation.z=wave>=0&&wave<2.3?-1.95+Math.sin(wave*8)*.16:-.12+Math.sin(t)*.035*motion;
        left.elbow.rotation.z=wave>=0&&wave<2.3?-.5+Math.sin(wave*10)*.32:0;
        right.joint.rotation.z=.12-Math.sin(t)*.035*motion;
        renderer.render(scene,camera);frames++;
    });
    container.dataset.atlasReady='true';
    return {
        setState(next,isActive=true){container.dataset.atlasMode=next;mode=['idle','thinking','speaking'].includes(next)?next:'idle';active=isActive;},
        wave(){waveAt=(performance.now()-started)/1000;},
        reset(){targetYaw=0;},
        setPortrait(enabled){camera.position.set(0,enabled?2.12:1.55,enabled?2.75:5.7);camera.lookAt(0,enabled?2.08:1.45,0);camera.updateProjectionMatrix();},
        getDiagnostics(){return {mode,active,frames,yaw,drawCalls:renderer.info.render.calls,triangles:renderer.info.render.triangles};},
        dispose(){if(disposed)return;disposed=true;renderer.setAnimationLoop(null);observer.disconnect();intersection.disconnect();canvas.removeEventListener('pointerdown',down);canvas.removeEventListener('pointermove',move);canvas.removeEventListener('pointerup',up);canvas.removeEventListener('pointercancel',up);canvas.removeEventListener('keydown',keydown);canvas.removeEventListener('webglcontextlost',contextLost);const geometries=new Set(),materials=new Set();scene.traverse(o=>{if(o.geometry)geometries.add(o.geometry);if(o.material)(Array.isArray(o.material)?o.material:[o.material]).forEach(m=>materials.add(m));});geometries.forEach(g=>g.dispose());materials.forEach(m=>m.dispose());renderer.dispose();renderer.forceContextLoss();delete container.dataset.atlasReady;}
    };
    } catch(error) {renderer?.dispose();renderer?.forceContextLoss();throw error;}
}
