const React=window.React;
const {useEffect,useRef,useState}=React;
const {createRoot}=window.ReactDOM;
const h=React.createElement;
const API="/api/ubuntu/azure/lesson1/sample";
const IMG="https://cdn.shopify.com/s/files/1/0712/9500/8877/files/ubuntu-talks-everyday-isizulu-beginner-i-hd.png?v=1795026974";
const CHECKOUT="https://whop.com/checkout/plan_KhrZ8JGb2YWRt";
const SITE="https://ubuntu-talks.whop.site";
const STAGES=["Hear","Understand","Imitate","Manipulate","Retrieve","Converse","Assess"];
const LESSONS=["Sounds, Greetings & Respect","Introduce Yourself","Family & Community","Requests & Everyday Needs","Food & Home","Numbers & Time","Places & Directions","Shopping & Prices","Everyday Small Talk","Beginner Conversation Capstone"];
const fmt=t=>{const v=Math.max(0,Math.floor(Number(t)||0));return Math.floor(v/60)+":"+String(v%60).padStart(2,"0")};
function useMedia(){
 const audio=useRef(null),rail=useRef(null),cardRefs=useRef([]);
 const [manifest,setManifest]=useState(null),[status,setStatus]=useState("Loading the private lesson sample…");
 const [error,setError]=useState(false),[playing,setPlaying]=useState(false),[time,setTime]=useState(0),[active,setActive]=useState(0),[heard,setHeard]=useState(false);
 const [ready,setReady]=useState(false);
 useEffect(()=>{
  let alive=true,controller=new AbortController();
  async function get(){
   for(let i=0;i<4;i++){
    try{
     const res=await fetch(API+"/synced-dialogue",{credentials:"same-origin",cache:"no-store",signal:controller.signal});
     if(!res.ok)throw Error("Media request "+res.status);
     const j=await res.json();
     if(j.version!=="native-greeting-lesson01-v1"||j.instructor_english_audio!==false||j.commercial_release!==false||!Array.isArray(j.cues)||j.cues.length<14)throw Error("Unverified media manifest");
     if(alive){setManifest(j);setReady(true);setStatus("Ready. Listen as the highlighted phrases follow the voices.");}
     return;
    }catch(e){if(i===3&&alive){setError(true);setStatus("The protected sample is unavailable. Refresh the page to retry.");}else await new Promise(r=>setTimeout(r,1500*(i+1)));}
   }
  }get();
  return()=>{alive=false;controller.abort()};
 },[]);
 useEffect(()=>{
  if(!manifest)return;
  const cues=manifest.cues,idx=Math.max(0,cues.findIndex((c,i)=>time>=c.start&&time<(cues[i+1]?.start??manifest.duration_seconds+1)));
  if(idx!==active)setActive(idx);
 },[time,manifest]);
 useEffect(()=>{
  const el=cardRefs.current[active];
  if(el&&rail.current&&playing){const node=rail.current;const target=el.offsetLeft-node.offsetLeft-(node.clientWidth-el.offsetWidth)/2;node.scrollTo({left:Math.max(0,target),behavior:'smooth'});}
 },[active,playing]);
 async function toggle(){
  const a=audio.current;if(!a)return;
  if(!a.paused){a.pause();return;}
  try{setStatus("Playing your private Lesson 1 preview.");setError(false);await a.play();}
  catch{setError(true);setStatus("Audio is unavailable. Try again after the private service wakes up.");}
 }
 async function jump(c,i){
  if(!audio.current)return;
  audio.current.currentTime=c.start;setTime(c.start);setActive(i);
  try{await audio.current.play()}catch{setStatus("Press Play to start the selected phrase.");}
 }
 const events={
  onTimeUpdate:e=>setTime(e.currentTarget.currentTime),
  onPlay:()=>setPlaying(true),
  onPause:()=>setPlaying(false),
  onEnded:()=>{setPlaying(false);setHeard(true);setStatus("Well done. Now try the greeting challenge below.");},
  onError:()=>{setError(true);setStatus("Audio connection interrupted. Press Play again to retry.");}
 };
 return {audio,rail,cardRefs,manifest,status,error,playing,time,active,heard,ready,toggle,jump,events};
}
function Modal({onClose}){
 useEffect(()=>{const close=e=>e.key==="Escape"&&onClose();document.addEventListener("keydown",close);return()=>document.removeEventListener("keydown",close)},[onClose]);
 return h("div",{className:"modal-backdrop",role:"presentation",onClick:onClose},
  h("section",{className:"modal",role:"dialog","aria-modal":"true","aria-labelledby":"did-title",onClick:e=>e.stopPropagation()},
   h("button",{className:"modal-close",onClick:onClose,"aria-label":"Close learning tip"},"×"),
   h("span",{className:"eyebrow"},"DID YOU KNOW?"),
   h("h2",{id:"did-title"},"One person. One group. A meaningful difference."),
   h("p",null,"In isiZulu, greetings change depending on who you are addressing. “Sawubona” greets one person; “Sanibonani” greets a group. Listen for both forms and try saying them aloud."),
   h("p",{className:"small-muted"},"The goal is not memorizing a translation. It is recognizing who you are speaking to and selecting the appropriate greeting."),
   h("button",{className:"button button-primary",onClick:onClose},"Got it — continue learning")));
}
function SideNav({onUnlock,onNavigate,open,onClose}){
 return h("aside",{className:"side "+(open?"side-open":""),"aria-label":"Course navigation"},
   h("div",{className:"side-brand"},h("div",{className:"side-badge"},"UT"),h("div",null,h("strong",null,"Ubuntu Talks"),h("small",null,"EVERYDAY ISIZULU")),h("button",{className:"mobile-close",onClick:onClose,"aria-label":"Close course menu"},"×")),
   h("div",{className:"course-thumb"},h("img",{src:IMG,alt:"Decorated African roundhouse course artwork"}),h("div",null,h("span",null,"BEGINNER I"),h("strong",null,"Everyday isiZulu"))),
   h("p",{className:"side-kicker"},"YOUR COURSE"),h("div",{className:"progress-rail"},h("span",{style:{width:"10%"}})),h("p",{className:"side-progress"},"Lesson 1 of 10 · Preview access"),
   h("nav",{className:"lesson-nav","aria-label":"Course lessons"},LESSONS.map((name,i)=>h("button",{type:"button",key:name,className:"lesson-button "+(i===0?"current":"locked"),onClick:()=>{onClose();i===0?onNavigate():onUnlock();}},
    h("span",{className:"lesson-number"},String(i+1).padStart(2,"0")),
    h("span",{className:"lesson-name"},name),
    h("span",{className:"lesson-lock","aria-label":i?"Locked lesson":"Preview available"},i?"🔒":"●")))),
   h("div",{className:"side-bottom"},h("span",null,"✦ Learn with purpose"),h("button",{type:"button",onClick:onUnlock,className:"sidebar-cta"},"Unlock the full course")));
}
function StageBar({onUnlock}){
 return h("div",{className:"stage-steps","aria-label":"Seven learning stages"},STAGES.map((name,i)=>h("button",{key:name,type:"button",className:"stage-step "+(i===0?"selected":"restricted"),onClick:()=>i?onUnlock():document.getElementById("hear").scrollIntoView({behavior:"smooth",block:"start"}),
  "aria-label":i?name+" stage, locked until enrollment":name+" stage, available"},
  h("span",{className:"stage-n"},String(i+1).padStart(2,"0")),h("span",null,name),i?h("span",{className:"lock","aria-hidden":"true"},"🔒"):null)));
}
function GreetingChallenge({onUnlock}){
 const [answer,setAnswer]=useState(""),[checked,setChecked]=useState(false);
 const correct=answer==="Sanibonani";
 return h("div",{className:"challenge"},
  h("div",null,h("span",{className:"eyebrow"},"YOUR FIRST SPEAKING CHALLENGE"),h("h3",null,"How do you greet a group?"),h("p",null,"Choose the expression, then say it aloud before checking.")),
  h("div",{className:"challenge-answers"},["Sawubona","Sanibonani"].map(a=>h("button",{type:"button",key:a,onClick:()=>{setAnswer(a);setChecked(false)},className:"choice "+(answer===a?"choice-selected":"")},a))),
  h("button",{className:"button button-dark",disabled:!answer,onClick:()=>setChecked(true)},"Check my answer"),
  checked?h("div",{className:"feedback "+(correct?"correct":"retry"),role:"status"},correct?"Yebo! Sanibonani greets a group. Say it aloud once more.":"Not quite. Sawubona greets one person. Try the group greeting."):null,
  h("div",{className:"challenge-footer"},h("span",null,"Ready for the next stage?"),h("button",{className:"text-button",onClick:onUnlock},"Continue to Understand →")));
}
function MrsUbuntuGuide(){
 return h("section",{className:"guide-card", "aria-label":"Mrs Ubuntu your learning guide"},
   h("div",{className:"guide-avatar","aria-hidden":"true"},"MU"),
   h("div",{className:"guide-message"},h("span",{className:"eyebrow"},"MRS UBUNTU · YOUR GUIDE"),
     h("h3",null,"Welcome. Every conversation starts with a greeting."),
     h("p",null,"First listen to Thando and Themba. Notice how a greeting changes when you speak to one person or a group. Then say the expression yourself."),
     h("span",{className:"guide-direction"},"1 · Listen  →  2 · Notice  →  3 · Speak")),
   h("span",{className:"guide-mode"},"INSTRUCTOR INTRODUCTION"));
}
function MicroQuest({onUnlock}){
 const [index,setIndex]=useState(0),[answers,setAnswers]=useState({}),[checked,setChecked]=useState(false);
 const qs=[
 {prompt:"You meet one neighbour. Which greeting fits?",choices:["Sawubona","Sanibonani"],correct:0,explain:"Sawubona addresses one person."},
 {prompt:"Now greet a group of friends.",choices:["Sawubona","Sanibonani"],correct:1,explain:"Sanibonani addresses more than one person."},
 {prompt:"Someone asks 'Unjani?' What could you say?",choices:["Ngiyaphila","Sanibonani"],correct:0,explain:"Ngiyaphila means 'I am fine.'"}
 ];
 const q=qs[index],answer=answers[index],passed=answer===q.correct;
 const complete=index===qs.length-1&&checked&&passed;
 return h("section",{className:"micro-quest", "aria-label":"Interactive greeting practice"},
  h("div",{className:"micro-top"},h("span",{className:"eyebrow"},"SPEAKING GAME · "+String(index+1).padStart(2,"0")+" / 03"),h("span",{className:"micro-score"},Object.values(answers).filter((a,i)=>a===qs[i].correct).length+" of 3")),
  h("div",{className:"micro-meter"},h("div",{style:{width:((index+1)/qs.length*100)+"%"}})),
  h("h3",null,q.prompt),
  h("p",{className:"micro-prompt"},"Choose an answer, then say it aloud."),
  h("div",{className:"micro-choices"},q.choices.map((choice,i)=>h("button",{key:choice,type:"button",
    className:"micro-choice "+(answer===i?"chosen":""),
    onClick:()=>{setAnswers({...answers,[index]:i});setChecked(false)}},
    h("span",{className:"micro-choice-icon"},String.fromCharCode(65+i)),choice))),
  checked?h("p",{className:"micro-feedback "+(passed?"win":"try"),role:"status"},passed?"✓ Correct. "+q.explain:"Try again. Think about who you are greeting."):null,
  h("div",{className:"micro-controls"},
    h("button",{className:"button button-dark",disabled:answer==null,onClick:()=>{if(!checked)setChecked(true);else if(passed&&index<qs.length-1){setIndex(index+1);setChecked(false)}else if(complete)onUnlock();}},
      checked&&passed?(complete?"Continue the course →":"Next challenge →"):"Check answer"),
    h("span",{className:"micro-celebrate"},complete?"✦ Excellent work!":"Small steps. Real conversations.")));
}
function App(){
 const media=useMedia();const [tip,setTip]=useState(false),[paywall,setPaywall]=useState(false),[mobileMenu,setMobileMenu]=useState(false);
 const contentRef=useRef(null);
 function goHear(){contentRef.current?.scrollIntoView({behavior:"smooth",block:"start"})}
 const d=media.manifest?.duration_seconds||0;
 return h(React.Fragment,null,
  h("div",{className:"app-shell"},
   h(SideNav,{onUnlock:()=>setPaywall(true),onNavigate:goHear,open:mobileMenu,onClose:()=>setMobileMenu(false)}),
   mobileMenu?h("button",{className:"mobile-scrim",onClick:()=>setMobileMenu(false),"aria-label":"Close course navigation"}):null,
   h("div",{className:"main-panel"},
    h("header",{className:"topbar"},
     h("button",{type:"button",className:"mobile-menu",onClick:()=>setMobileMenu(true),"aria-label":"Open lesson navigation"},"☰"),
     h("a",{className:"top-logo",href:"https://ubuntu-talks.whop.site/"},"Ubuntu",h("span",null," Talks")),
     h("span",{className:"top-course"},"Everyday isiZulu",h("span",null," / Beginner I")),
     h("div",{className:"top-actions"},h("button",{className:"help-button",onClick:()=>setTip(true)},"?  Learning tip"),h("a",{className:"top-enroll",href:SITE+"/dashboard"},"My Dashboard"),h("details",{className:"top-more"},h("summary",null,"More"),h("div",{className:"top-more-list"},h("a",{href:SITE},"Home"),h("a",{href:SITE+"/#languages"},"Languages"),h("a",{href:SITE+"/my-courses"},"My courses"),h("a",{href:SITE+"/help"},"Help"))),h("button",{className:"top-enroll top-enroll-strong",onClick:()=>setPaywall(true)},"Continue course"))),
    h("main",{className:"content",ref:contentRef,id:"hear"},
     h("nav",{className:"breadcrumbs","aria-label":"Breadcrumb"},h("span",null,"Your classroom"),h("span",null,"›"),h("span",null,"Lesson 01")),
     h("section",{className:"hero-banner"},
      h("div",{className:"hero-writing"},h("span",{className:"hero-kicker"},"UBUNTU TALKS  /  EVERYDAY ISIZULU"),h("h1",null,"Greetings &",h("span",null," Respect")),h("p",null,"One greeting opens a conversation. Let's begin."),h("div",{className:"hero-meta"},h("span",null,"◉  Lesson 01"),h("span",null,"◷  Lesson 1 · Hear"))),
      h("div",{className:"hero-visual"},h("img",{src:IMG,alt:"Traditional African roundhouse with vibrant geometric artwork in golden light"})),
      null),
     h(MrsUbuntuGuide),h("div",{className:"welcome-line"},h("div",null,h("span",{className:"eyebrow"},"WELCOME TO LESSON ONE"),h("h2",null,"Every conversation begins here."),h("p",null,"Mrs Ubuntu guides your learning while Thando and Themba demonstrate the language. Listen, notice and speak aloud. Continue through the seven learning stages as your course access unlocks.")),h("button",{className:"tip-card",onClick:()=>setTip(true)},"✦",h("span",null,h("strong",null,"Did you know?"),h("small",null,"See a quick cultural insight")))),
     h("div",{className:"lesson-workspace"},h("div",{className:"lesson-main"},
      h("section",{className:"lesson-step"},
       h("div",{className:"stage-heading"},h("div",null,h("span",{className:"eyebrow"},"01 / 07  ·  HEAR"),h("h2",null,"Listen to the conversation.")),h("span",{className:"preview-tag"},"LESSON 01 · HEAR")),
       h("p",{className:"stage-intro"},"Listen once, following Thando and Themba. Then replay any phrase and repeat it aloud. The highlighted card moves with the audio."),
       h("div",{className:"audio-player"},
        h("div",{className:"audio-controls"},h("button",{className:"play-main",disabled:!media.ready,onClick:media.toggle,"aria-label":media.playing?"Pause audio":"Play lesson audio"},media.playing?"Ⅱ":"▶"),
          h("div",{className:"audio-details"},h("strong",null,"Greetings · Guided conversation"),h("span",null,media.ready?fmt(media.time)+" / "+fmt(d):"Preparing the private sample…")),h("span",{className:"audio-voice"},"Thando + Themba")),
        h("input",{className:"seek",type:"range",min:0,max:d||1,step:.05,value:Math.min(media.time,d||1),disabled:!media.ready,
           onChange:e=>{if(media.audio.current){media.audio.current.currentTime=Number(e.target.value);media.setTime?.(Number(e.target.value))}},"aria-label":"Seek sample audio"}),
        h("audio",{ref:media.audio,preload:"metadata",src:media.ready?API+"/native-only.mp3":undefined,...media.events})),
       h("p",{className:"media-state "+(media.error?"media-error":""),role:"status"},media.status),
       h("div",{className:"transcript-bar"},h("strong",null,"Follow the conversation"),h("span",null,"Swipe or tap to replay a line")),
       h("div",{className:"dialogue-strip",ref:media.rail,role:"list",tabIndex:0,"aria-label":"Horizontal synchronized isiZulu dialogue"},
        media.manifest?.cues?.map((cue,i)=>h("button",{type:"button",key:cue.cue,ref:el=>media.cardRefs.current[i]=el,
          className:"dialogue-card "+(i===media.active?"active":""),onClick:()=>media.jump(cue,i),
          "aria-current":i===media.active?"true":undefined,role:"listitem",
          "aria-label":cue.speaker+" says "+cue.text},
          h("span",{className:"speaker"},"●  "+cue.speaker),
          h("strong",{lang:"zu"} ,cue.text),
          cue.meaning?h("span",{className:"meaning"},cue.meaning):h("span",{className:"meaning"},"Listen, then repeat.")))||h("p",{className:"loading"},"Preparing verified dialogue…")),
       h("p",{className:"gesture-hint"},"↔  Swipe to explore · Cards highlight automatically as the audio plays."),
       h(MicroQuest,{onUnlock:()=>setPaywall(true)}))),
     h("div",{className:"lesson-right"},h("section",{className:"path-card"},h("span",{className:"eyebrow"},"YOUR LEARNING PATH"),h("h3",null,"Your learning journey"),h("p",null,"A clear journey from listening to using the language confidently."),h(StageBar,{onUnlock:()=>setPaywall(true)})),
      h("div",{className:"sidebar-invite"},h("span",null,"✦"),h("strong",null,"Learn in context"),h("p",null,"Practice, retrieve and speak naturally. The full classroom continues after this free first step."),h("button",{onClick:()=>setPaywall(true)},"Unlock all seven stages →")))),
    h("section",{className:"closing-cta"},h("div",null,h("span",{className:"eyebrow"},"THE NEXT CONVERSATION STARTS HERE"),h("h2",null,"Ready to speak with confidence?"),h("p",null,"Join the guided course for the remaining activities, practice and speaking assessment.")),h("button",{className:"button button-primary",onClick:()=>setPaywall(true)},"Explore enrollment  →")),
    h("footer",null,"Ubuntu Talks · Language connects us  ·  Private Lesson 1 staging review")))),
  tip?h(Modal,{onClose:()=>setTip(false)}):null,
  paywall?h("div",{className:"modal-backdrop",onClick:()=>setPaywall(false),role:"presentation"},h("section",{className:"modal paywall",role:"dialog","aria-modal":"true","aria-labelledby":"unlock-title",onClick:e=>e.stopPropagation()},h("button",{className:"modal-close",onClick:()=>setPaywall(false),"aria-label":"Close enrollment dialog"},"×"),h("span",{className:"eyebrow"},"CONTINUE YOUR LEARNING"),h("h2",{id:"unlock-title"},"Continue your learning journey."),h("p",null,"Your lesson continues through Understand, Imitate, Manipulate, Retrieve, Converse and Assess. Enroll to unlock the remaining stages."),h("p",{className:"commercial-note"},"This is a private production preview. The full commercial course has not yet been released; do not purchase solely to test."),h("a",{className:"button button-primary",href:CHECKOUT,target:"_blank",rel:"noopener noreferrer"},"Review $29.99 checkout ↗"),h("button",{className:"button button-outline",onClick:()=>setPaywall(false)},"Continue the preview"))):null
 );
}
createRoot(document.getElementById("app")).render(h(App));
