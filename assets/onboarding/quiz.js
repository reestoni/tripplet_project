/* Quiz / Lernnachweis fuer Onboarding-Module (Nutzerwunsch 2026-11-06).
   Einbinden: <script src="quiz.js"></script> NACH dem Hauptskript der Seite.
   Fragen in <key>_texts.js als TEXTS[lang].quiz = [{q, a:[...], c:<Index richtige Antwort>, e:<Erklaerung>, sc:<Szene 0..>}].
   Das Quiz ist der Reiter nach der letzten Szene: window.goScene(<Anzahl Szenen>) zeigt es.
   Eingebettet meldet die Seite das Ergebnis per document.title = "quiz:<richtig>:<total>" (ui/screen_onboarding.py
   speichert es). PASS muss zu ui/onboarding_catalog.QUIZ_PASS passen. Keine externen Ressourcen. */
(()=>{
const PASS=0.8;
const UI={
 de:{tab:'Quiz',title:'Quiz · {h}',intro:'Beantworte die Fragen zu den Szenen. Ab {p} % richtig gilt das Thema als bestanden. Zu jeder Frage kannst du die passende Szene nochmals ansehen.',
  progress:'{n} von {t} beantwortet · {r} richtig',right:'Richtig.',wrong:'Leider falsch.',review:'Szene „{s}“ nochmals ansehen',
  result:'{r} von {t} richtig ({p} %)',passed:'Bestanden. Gut gemacht!',failed:'Noch nicht bestanden. Schau dir die Szenen nochmals an und versuch es erneut.',again:'Neu starten'},
 en:{tab:'Quiz',title:'Quiz · {h}',intro:'Answer the questions about the scenes. With {p} % correct the topic counts as passed. For every question you can look at the matching scene again.',
  progress:'{n} of {t} answered · {r} correct',right:'Correct.',wrong:'Not quite.',review:'Look at scene “{s}” again',
  result:'{r} of {t} correct ({p} %)',passed:'Passed. Well done!',failed:'Not passed yet. Look at the scenes again and try once more.',again:'Start again'},
 es:{tab:'Quiz',title:'Quiz · {h}',intro:'Responde las preguntas sobre las escenas. Con un {p} % de aciertos el tema se considera aprobado. Para cada pregunta puedes volver a ver la escena correspondiente.',
  progress:'{n} de {t} respondidas · {r} correctas',right:'Correcto.',wrong:'Incorrecto.',review:'Volver a ver la escena «{s}»',
  result:'{r} de {t} correctas ({p} %)',passed:'Aprobado. ¡Bien hecho!',failed:'Todavía no aprobado. Vuelve a ver las escenas e inténtalo de nuevo.',again:'Empezar de nuevo'},
 zh:{tab:'测验',title:'测验 · {h}',intro:'回答关于各场景的问题。正确率达到 {p} % 即视为通过本主题。每道题都可以回看对应的场景。',
  progress:'已答 {n} / {t} · 答对 {r}',right:'正确。',wrong:'不对。',review:'回看场景“{s}”',
  result:'答对 {r} / {t}（{p} %）',passed:'已通过，做得好！',failed:'尚未通过。请再看一遍各场景，然后重试。',again:'重新开始'}};
if(!window.TEXTS||!window.goScene)return;
const $=id=>document.getElementById(id);
const lang=()=>{const l=document.documentElement.lang;return TEXTS[l]?l:(TEXTS.de?'de':Object.keys(TEXTS)[0])};
const U=()=>UI[lang()]||UI.en;
const Q=()=>TEXTS[lang()].quiz||[];
if(!Q().length)return;
const nSc=()=>TEXTS[lang()].scenes.length;
const fmt=(s,o)=>s.replace(/\{(\w+)\}/g,(_,k)=>o[k]);
const EMBED=document.body.classList.contains('embedded');

const css=document.createElement('style');css.textContent=`
#quiz{display:none;background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:22px 28px 26px}
body.quizmode #quiz{display:block}
body.quizmode .stage,body.quizmode .controls .right,body.quizmode .caption,body.quizmode .note{display:none!important}
#quiz h2{font-family:var(--font-display);font-weight:700;font-size:30px;line-height:1.1;margin:0 0 8px}
#quiz .qintro{color:var(--muted);margin:0 0 6px;max-width:80ch}
#quiz .qprog{font-family:var(--font-mono);font-size:13px;color:var(--hl);margin:0 0 6px}
#quiz .qcard{display:grid;grid-template-columns:40px minmax(0,1fr);gap:12px;border-top:1px solid var(--line);padding:16px 0 14px}
#quiz .qnum{font-family:var(--font-display);font-weight:700;font-size:28px;line-height:1.1;color:var(--muted)}
#quiz .qcard.done-ok .qnum{color:var(--hl)}#quiz .qcard.done-bad .qnum{color:#D6453D}
#quiz .qq{font-weight:600;margin:0 0 10px;font-size:16px}
#quiz .qans{display:flex;flex-direction:column;gap:6px;max-width:820px}
#quiz .qans button{justify-content:flex-start;text-align:left;width:100%;line-height:1.35}
#quiz .qans button:disabled{cursor:default;color:var(--fg)}
#quiz .qans button.ok{background:#E9F6E9;border-color:var(--hl)}
#quiz .qans button.bad{background:#FBE9E7;border-color:#D6453D}
#quiz .qans button.dim{opacity:.55}
#quiz .qfb{margin:10px 0 0;font-size:14px;max-width:820px}
#quiz .qfb b.ok{color:var(--hl)}#quiz .qfb b.bad{color:#D6453D}
#quiz .qfb a{color:var(--air);cursor:pointer;text-decoration:underline;margin-left:6px}
#quiz .qres{border:2px solid var(--line);border-radius:8px;padding:16px 20px;margin-top:6px}
#quiz .qres.pass{border-color:var(--hl);background:#E9F6E9}#quiz .qres.fail{border-color:#E07B39;background:#FBF1E8}
#quiz .qres .big{font-family:var(--font-display);font-weight:700;font-size:30px;margin:0 0 4px}
#quiz .qres p{margin:0 0 12px}`;
document.head.appendChild(css);
const box=document.createElement('section');box.id='quiz';box.setAttribute('aria-live','polite');
const stage=document.querySelector('.stage');stage.parentNode.insertBefore(box,stage);

let active=false,order=[],picked=[];
function shuffle(n){const a=[...Array(n).keys()];for(let i=n-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[a[i],a[j]]=[a[j],a[i]]}return a}
function reset(){order=Q().map(q=>shuffle(q.a.length));picked=Q().map(()=>-1)}
reset();
const el=(tag,cls,txt)=>{const e=document.createElement(tag);if(cls)e.className=cls;if(txt!=null)e.textContent=txt;return e};
function stats(){let n=0,r=0;Q().forEach((q,i)=>{if(picked[i]>=0){n++;if(picked[i]===q.c)r++}});return{n,r,t:Q().length}}
function render(){const u=U(),qs=Q(),sc=TEXTS[lang()].scenes,st=stats();box.innerHTML='';
  box.append(el('h2',null,fmt(u.title,{h:(TEXTS[lang()].ui||{}).h1||''})),el('p','qintro',fmt(u.intro,{p:Math.round(PASS*100)})),
    el('p','qprog',fmt(u.progress,{n:st.n,t:st.t,r:st.r})));
  qs.forEach((q,i)=>{const done=picked[i]>=0,card=el('div','qcard'+(done?(picked[i]===q.c?' done-ok':' done-bad'):''));
    card.append(el('div','qnum',String(i+1)));const body=el('div');body.append(el('p','qq',q.q));
    const ans=el('div','qans');order[i].forEach(k=>{const b=el('button',null,q.a[k]);b.type='button';
      if(done){b.disabled=true;if(k===q.c)b.classList.add('ok');else if(k===picked[i])b.classList.add('bad');else b.classList.add('dim')}
      else b.onclick=()=>{picked[i]=k;render();report()};ans.append(b)});
    body.append(ans);
    if(done){const fb=el('p','qfb');fb.append(el('b',picked[i]===q.c?'ok':'bad',picked[i]===q.c?u.right:u.wrong),document.createTextNode(' '+q.e));
      if(sc[q.sc]){const a=el('a',null,fmt(u.review,{s:sc[q.sc].k}));a.onclick=()=>window.goScene(q.sc);fb.append(a)}body.append(fb)}
    card.append(body);box.append(card)});
  if(st.n===st.t){const p=Math.round(100*st.r/st.t),ok=st.r/st.t>=PASS-1e-9,res=el('div','qres '+(ok?'pass':'fail'));
    res.append(el('p','big',fmt(u.result,{r:st.r,t:st.t,p})),el('p',null,ok?u.passed:u.failed));
    const b=el('button',null,u.again);b.type='button';b.onclick=()=>{reset();render();if(EMBED)document.title='scene:'+nSc();box.scrollIntoView({block:'start'})};res.append(b);box.append(res)}}
function report(){const st=stats();if(st.n===st.t&&EMBED)document.title=`quiz:${st.r}:${st.t}`}
function markBtn(){const b=$('quizbtn');if(b)b.setAttribute('aria-pressed',active)}
function show(){active=true;document.body.classList.add('quizmode');render();markBtn();if(EMBED)document.title='scene:'+nSc();scrollTo(0,0)}
function hide(){if(!active)return;active=false;document.body.classList.remove('quizmode');markBtn()}
function addBtn(){const sc=$('scenes');if(!sc||$('quizbtn'))return;const b=document.createElement('button');b.type='button';b.id='quizbtn';
  b.innerHTML='<span>?</span>';b.append(U().tab);b.onclick=e=>{e.stopPropagation();[...sc.children].forEach(x=>x.setAttribute('aria-pressed',x===b));show()};sc.appendChild(b);markBtn()}
/* andere Szenen-Knoepfe (nur ohne Einbettung sichtbar) beenden das Quiz */
const scEl=$('scenes');if(scEl)scEl.addEventListener('click',e=>{if(e.target.closest('button')&&e.target.closest('button').id!=='quizbtn')hide()},true);
/* Pfeiltasten/Leertaste steuern die Animation - im Quiz nicht */
addEventListener('keydown',e=>{if(active&&(e.key==='ArrowLeft'||e.key==='ArrowRight'||e.key===' ')&&e.target.tagName!=='BUTTON')e.stopImmediatePropagation()},true);
const origGo=window.goScene,origLang=window.setLang;
window.goScene=i=>{if(i>=nSc()){show();return}hide();origGo(i)};
window.setLang=l=>{origLang(l);addBtn();if(active){render();if(EMBED)document.title='scene:'+nSc();[...$('scenes').children].forEach(x=>x.setAttribute('aria-pressed',x.id==='quizbtn'))}};
addBtn();
const p=new URLSearchParams(location.search);if(p.get('quiz')==='1')show();
})();
