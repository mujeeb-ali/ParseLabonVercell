import React, { useEffect, useMemo, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Activity, ArrowDownRight, ArrowLeft, ArrowRight, BookOpen, Braces, ChevronDown, CircleHelp, Code2, Command, FileCode2, FlaskConical, GitBranch, Layers3, Menu, Play, RotateCcw, Share2, Download, Sun, Moon, Monitor, Search, Settings2, Sparkles, Workflow, X } from 'lucide-react';
import './style.css';
import './extra.css';
import './dark.css';

const API = import.meta.env.VITE_API_URL || '/api';
const modules = [
  { id:'overview', label:'Overview', icon:Activity, group:'LAB' },
  { id:'lexer', label:'Lexical analysis', icon:Code2, group:'FRONT END' },
  { id:'automata', label:'Automata studio', icon:Workflow, group:'FRONT END' },
  { id:'grammar', label:'Grammar workbench', icon:Braces, group:'FRONT END' },
  { id:'ll1', label:'LL(1) parsing', icon:GitBranch, group:'PARSING' },
  { id:'slr', label:'LR parsing', icon:Layers3, group:'PARSING' },
  { id:'timemachine', label:'Time machine', icon:RotateCcw, group:'PARSING' },
  { id:'examples', label:'Experiments', icon:FlaskConical, group:'REFERENCE' },
  { id:'docs', label:'Field notes', icon:BookOpen, group:'REFERENCE' },
];
const defaults = {
  lexer: { source:'total = price * 12 + tax;', rules:[{name:'ID',pattern:'[a-zA-Z_][a-zA-Z0-9_]*'},{name:'NUM',pattern:'[0-9]+'},{name:'OP',pattern:'[+*/=-]'},{name:'SEMI',pattern:';'},{name:'WS',pattern:'[ \\t\\n]+',skip:true}] },
  automata:{pattern:'(a|b)*abb'},
  grammar:{grammar:"E  -> E + T | T\nT  -> T * F | F\nF  -> ( E ) | id",input:'id + id * id'},
  ll1:{grammar:"E  -> T E'\nE' -> + T E' | ε\nT  -> F T'\nT' -> * F T' | ε\nF  -> ( E ) | id",input:'id + id * id'},
  slr:{grammar:'E -> E + T | T\nT -> T * F | F\nF -> ( E ) | id',input:'id + id * id',method:'slr'},
  timemachine:{source:'x + y * z',grammar:"E  -> T E'\nE' -> + T E' | ε\nT  -> F T'\nT' -> * F T' | ε\nF  -> ( E ) | id",mode:'ll',tokenMap:{ID:'id',PLUS:'+',STAR:'*',LPAREN:'(',RPAREN:')',WS:' '},rules:[{name:'ID',pattern:'[a-zA-Z_][a-zA-Z0-9_]*'},{name:'PLUS',pattern:'\\+'},{name:'STAR',pattern:'\\*'},{name:'LPAREN',pattern:'\\('},{name:'RPAREN',pattern:'\\)'},{name:'WS',pattern:' +',skip:true}]}
};

async function request(path, body) {
  const res = await fetch(`${API}${path}`, {method:body?'POST':'GET',headers:body?{'Content-Type':'application/json'}:{},body:body?JSON.stringify(body):undefined});
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || `Request failed (${res.status})`);
  return data;
}
function App(){
  const [page,setPage]=useState(()=>readShare().page||'overview'),[data,setData]=useState(null),[error,setError]=useState(''),[busy,setBusy]=useState(false),[examples,setExamples]=useState([]),[picked,setPicked]=useState(null),[step,setStep]=useState(0),[mobile,setMobile]=useState(false),[health,setHealth]=useState(false);
  const [form,setForm]=useState(()=>{const base=Object.fromEntries(Object.entries(defaults).map(([k,v])=>[k,JSON.parse(JSON.stringify(v))]));const sh=readShare();if(sh.page&&sh.data&&base[sh.page])base[sh.page]={...base[sh.page],...sh.data};return base});
  const [toast,setToast]=useState('');
  useEffect(()=>{try{const h=`#/${page}`;if(!location.hash.startsWith(h+'?'))history.replaceState(null,'',h)}catch{}},[page]);
  async function share(){const url=shareUrl(page,form[page]);try{history.replaceState(null,'',url.slice(url.indexOf('#')));await navigator.clipboard.writeText(url);setToast('Link copied. Anyone who opens it sees this exact experiment.')}catch{setToast('Copy this link from the address bar to share the experiment.')}setTimeout(()=>setToast(''),3200)}
  const [nonce,setNonce]=useState(0);
  const [engine,setEngine]=useState(null);
  const nav=modules.find(x=>x.id===page)||modules[0];
  const update=(key,value)=>setForm(f=>({...f,[page]:{...f[page],[key]:value}}));
  const runRef=useRef(null);
  // Only show a result on the bench that produced it (avoids a one-frame render of stale data after navigation).
  const current=data&&data.__page===page?data:null;
  useEffect(()=>{request('/health').then(x=>{setHealth(true);setEngine(x)}).catch(()=>setHealth(false));request('/examples').then(x=>setExamples(x.examples||[])).catch(()=>{});},[]);
  useEffect(()=>{setData(null);setError('');setStep(0);if(page==='lexer'||page==='automata'||page==='grammar'||page==='ll1'||page==='slr'||page==='timemachine')run();},[page,nonce]);
  useEffect(()=>{const onKey=e=>{if((e.ctrlKey||e.metaKey)&&e.key==='Enter'){e.preventDefault();runRef.current?.()}};window.addEventListener('keydown',onKey);return()=>window.removeEventListener('keydown',onKey)},[]);
  runRef.current=()=>run();
  // Follow share links pasted into an already-open tab (only the #hash changes, so the page does not reload).
  useEffect(()=>{const onHash=()=>{const sh=readShare();if(!sh.page)return;if(sh.data)setForm(f=>({...f,[sh.page]:{...f[sh.page],...sh.data}}));setPicked(null);setPage(sh.page);setNonce(n=>n+1)};window.addEventListener('hashchange',onHash);return()=>window.removeEventListener('hashchange',onHash)},[]);
  function resetPage(){setForm(f=>({...f,[page]:JSON.parse(JSON.stringify(defaults[page]))}));setPicked(null);setNonce(n=>n+1)}
  function openInTimeMachine(source){setForm(f=>({...f,timemachine:{...f.timemachine,source,grammar:HERO_GRAMMAR,rules:JSON.parse(JSON.stringify(HERO_RULES)),tokenMap:{...HERO_MAP},mode:'ll'}}));setPicked(null);setPage('timemachine');setMobile(false);setNonce(n=>n+1)}
  function applyGrammar(text){update('grammar',text);setNonce(n=>n+1)}
  async function run(overrides){
    const forPage=page; const f={...form[page],...overrides}; setBusy(true);setError('');setStep(0);
    try{let d;
      if(page==='lexer')d=await request('/lexer/analyze',f);
      else if(page==='automata')d=await request('/regex/analyze',f);
      else if(page==='grammar')d=await request('/grammar/analyze',f);
      else if(page==='ll1')d=await request('/ll1/analyze',f);
      else if(page==='slr')d=await request('/lr/analyze',{...f,method:f.method||'slr'});
      else if(page==='timemachine')d=await request('/timemachine',f);
      if((forPage==='ll1'||forPage==='slr'||forPage==='grammar')&&d.valid){d.classes=await request('/grammar/classify',{grammar:f.grammar}).catch(()=>null)}
      setData({...d,__page:forPage});
    }catch(e){setError(e.message);setData(null)}finally{setBusy(false)}
  }
  function navigate(id){setPage(id);setMobile(false);setPicked(null)}
  async function loadExample(ex){let target=ex.kind==='lexer'?'lexer':ex.kind==='regex'?'automata':ex.kind==='ll1'?'ll1':ex.kind==='slr'?'slr':ex.kind==='timemachine'?'timemachine':'grammar';setForm(f=>({...f,[target]:{...f[target],...(target==='slr'?{method:'slr'}:{}),...ex.payload}}));setPage(target);setPicked(null);setMobile(false);setNonce(n=>n+1);}
  return <div className="shell">{toast&&<div className="toast" role="status">{toast}</div>}
    <aside className={`sidebar ${mobile?'show':''}`}><div className="brand"><div className="brand-mark"><span>p</span><i/></div><div><b>ParseLab</b><small>COMPILER LABORATORY</small></div><button className="icon-button close-mobile" onClick={()=>setMobile(false)}><X size={17}/></button></div>
      <div className="side-scroll">{['LAB','FRONT END','PARSING','REFERENCE'].map(g=><section className="nav-group" key={g}><div className="group-label">{g}</div>{modules.filter(m=>m.group===g).map(m=><button key={m.id} className={`nav-item ${page===m.id?'active':''}`} onClick={()=>navigate(m.id)}><m.icon size={16} strokeWidth={1.8}/><span>{m.label}</span>{m.id==='timemachine'&&<span className="nav-new">NEW</span>}</button>)}</section>)}</div>
      <div className="sidebar-bottom"><div className={`engine-status ${health?'online':''}`}><span className="status-dot"/><div><b>{health?'Engine connected':'Engine offline'}</b><small>{health?'FastAPI · /api':'Start the ParseLab API'}</small></div></div><div className="profile"><div className="avatar">PL</div><div><b>Laboratory session</b><small>Local workspace</small></div><Settings2 size={16}/></div></div>
    </aside>
    {mobile&&<button aria-label="Close menu" className="scrim" onClick={()=>setMobile(false)}/>}
    <main className="main"><header className="topbar"><button className="icon-button menu-button" onClick={()=>setMobile(true)}><Menu size={19}/></button><div className="crumb"><span>ParseLab</span><ArrowRight size={13}/><b>{nav.label}</b></div><div className="top-actions"><ThemeToggle/><div className="api-pill"><span className={`status-dot ${health?'':'offline'}`}/>{health?'API ready':'API disconnected'}</div><button className="help-button" onClick={()=>navigate('docs')}><CircleHelp size={15}/> Help</button></div></header>
      <div className="page-wrap">
        {page==='overview'?<Overview navigate={navigate} examples={examples} health={health} onExample={loadExample} onTry={openInTimeMachine} engine={engine}/>:page==='examples'?<Examples examples={examples} onExample={loadExample}/>:page==='docs'?<Docs/>:<>
          <div className="page-heading"><div><div className="eyebrow"><span>PARSELAB / {String(modules.findIndex(x=>x.id===page)).padStart(2,'0')}</span><span className="eyebrow-line"/><span>LIVE EXPERIMENT</span></div><h1>{heading(page)}</h1><p>{subheading(page)}</p></div><div className="heading-actions"><button className="button secondary" onClick={share} title="Copy a link that reopens this exact experiment"><Share2 size={14}/> Share</button><button className="button secondary" onClick={resetPage} title="Restore this bench's default input"><RotateCcw size={14}/> Reset</button><button className="button primary" onClick={()=>run()} disabled={busy}><Play size={14} fill="currentColor"/>{busy?'Computing…':'Run analysis'} <kbd>⌘ ↵</kbd></button></div></div>
          {error&&<div className="error-banner">{error}<button onClick={()=>run()}>Retry</button></div>}
          <div className="workbench"><section className="work-main"><EditorPanel page={page} form={form[page]} update={update} onRun={run} syntax={busy?{state:'busy'}:current?(current.valid===false?{state:'bad',msg:describeError(current)}:{state:'ok'}):null}/>{current&&<Output page={page} data={current} picked={picked} setPicked={setPicked} step={step} setStep={setStep} probe={form[page]?.probe} grammarText={form[page]?.grammar} onApply={applyGrammar}/>}</section><aside className="inspector"><Inspector page={page} data={current} busy={busy} navigate={navigate}/></aside></div>
        </>}
      </div>
    </main>
  </div>
}
function heading(p){return {lexer:'Lexical analysis',automata:'Automata studio',grammar:'Grammar workbench',ll1:'Predictive parsing',slr:'LR parsing studio',timemachine:'Compiler time machine'}[p]}
function subheading(p){return {lexer:'Define token rules and watch source become a positioned stream.',automata:'Follow Thompson’s construction from expression to deterministic machine.',grammar:'Read the structure of a grammar through sets, diagnostics, transforms and derivations.',ll1:'Trace every predictive decision from FIRST and FOLLOW to acceptance.',slr:'Build SLR(1), LALR(1) or canonical LR(1) automata and watch shifts and reductions unfold.',timemachine:'Move through a real compiler trace, from source characters to a parse tree.'}[p]}
function Overview({navigate,examples,health,onExample,onTry,engine}){
 const [src,setSrc]=useState(HERO_SAMPLES[0][0]);
 const [live,setLive]=useState(null);
 useEffect(()=>{const onKey=e=>{const tag=(e.target.tagName||'').toLowerCase();if(tag==='input'||tag==='textarea'||e.ctrlKey||e.metaKey||e.altKey)return;const n=Number(e.key);if(n>=1&&n<=BENCHES.length)navigate(BENCHES[n-1][0])};window.addEventListener('keydown',onKey);return()=>window.removeEventListener('keydown',onKey)},[navigate]);
 const moduleCount=engine?.modules?.length;
 return <div className="overview">
  <div className="hero-kicker"><span className="live-mark"/> INTERACTIVE COMPILER LAB <span className="hero-rule"/> VOL. 01 / 2026</div>
  <div className="hero"><div className="hero-copy"><h1>See how<br/>languages <em>come</em><br/>to life<span className="period">.</span></h1><p>Every source file has a journey. Type an expression and watch the real engine scan, tokenize and parse it, one transformation at a time.</p><div className="hero-buttons"><button className="button primary large" onClick={()=>navigate('lexer')}>Enter the laboratory <ArrowRight size={16}/></button><button className="text-button" onClick={()=>document.getElementById('journey')?.scrollIntoView({behavior:'smooth'})}>Follow your input <ArrowDownRight size={15}/></button></div><div className="hero-meta"><span><span className={`status-dot ${health?'':'offline'}`}/> {health?'ENGINE ONLINE':'CONNECT ENGINE TO BEGIN'}</span><span>{moduleCount?`${moduleCount} COMPUTATION MODULES`:'COMPUTATION MODULES'}</span>{engine?.version&&<span>v{engine.version}</span>}</div></div><LivePipeline health={health} onOpen={onTry} src={src} setSrc={setSrc} onResult={setLive}/></div>
  <Journey live={live} src={src} health={health} onOpen={()=>onTry(src)}/>
  <LaunchGrid navigate={navigate}/>
  <ExampleStrip examples={examples} onExample={onExample}/>
  <footer className="footer"><span>PARSELAB <i>·</i> EVERY LANGUAGE HAS A JOURNEY.</span><span>{health?`ENGINE ONLINE · ${moduleCount||''} MODULES`:'ENGINE OFFLINE'} <i>·</i> PRESS 1–6 TO OPEN A BENCH</span></footer>
 </div>}
function EditorPanel({page,form,update,onRun,syntax}){
 const f=form||{};
 const fileName={lexer:'lexer.rules',automata:'expression.regex',grammar:'grammar.cfg',ll1:'predictive.cfg',slr:'slr.cfg',timemachine:'experiment.trace'}[page];
 const setRule=(i,patch)=>update('rules',(f.rules||[]).map((x,j)=>j===i?{...x,...patch}:x));
 const ruleList=<div className="rule-list">{(f.rules||[]).map((r,i)=><div className="rule-row" key={i}><span className="rule-num">{String(i+1).padStart(2,'0')}</span><input aria-label="Token name" value={r.name} onChange={e=>setRule(i,{name:e.target.value})}/><span className="rule-arrow">←</span><input className="mono-input" aria-label="Regular expression" value={r.pattern} onChange={e=>setRule(i,{pattern:e.target.value})}/><label className="skip-toggle"><input type="checkbox" checked={!!r.skip} onChange={e=>setRule(i,{skip:e.target.checked})}/><span>skip</span></label><button className="remove-rule" aria-label="Remove rule" onClick={()=>update('rules',f.rules.filter((_,j)=>j!==i))}>×</button></div>)}<button className="add-rule" onClick={()=>update('rules',[...(f.rules||[]),{name:'TOKEN',pattern:'[a-z]+'}])}>＋ Add token rule</button></div>;
 const codeBox=(value,key,label,big)=><div className={`code-editor ${big?'big-editor':''}`}><div className="line-numbers">{(value||'').split('\n').map((_,i)=><span key={i}>{big?String(i+1).padStart(2,'0'):i+1}</span>)}</div><textarea spellCheck="false" value={value||''} onChange={e=>update(key,e.target.value)} aria-label={label}/></div>;
 return <div className="editor-panel"><div className="panel-head"><div className="tab-row"><span className="file-icon">⌘</span><b>{fileName}</b><span className="dirty-dot"/></div><div className="head-meta">{page==='automata'?'REGEX SYNTAX':page==='lexer'?'TOKEN SPECIFICATION':'GRAMMAR NOTATION'} <button className="icon-button" title="Run (Ctrl+Enter)" onClick={()=>onRun()}><Command size={13}/></button></div></div>
 {page==='lexer'&&<><div className="editor-subtitle">TOKEN RULES <span>ORDER CONTROLS PRIORITY</span></div>{ruleList}<div className="editor-subtitle source-label">SOURCE CODE <span>UTF-8 · LF</span></div>{codeBox(f.source,'source','Source code')}</>}
 {page==='automata'&&codeBox(f.pattern,'pattern','Regular expression',true)}
 {['grammar','ll1','slr','timemachine'].includes(page)&&codeBox(f.grammar,'grammar','Grammar',true)}
 {page==='timemachine'&&<><div className="mode-toggle"><span>PARSER</span>{[['ll','LL(1) · top-down'],['slr','SLR(1) · bottom-up']].map(([m,l])=><button key={m} className={(f.mode||'ll')===m?'on':''} onClick={()=>{update('mode',m);onRun({mode:m})}}>{l}</button>)}</div><div className="editor-subtitle source-label">SOURCE PROGRAM <span>LEXED, MAPPED, THEN PARSED</span></div>{codeBox(f.source,'source','Source program')}<details className="rules-details"><summary>Lexer rules and token → terminal map ({(f.rules||[]).length}) <ChevronDown size={13}/></summary>{ruleList}<div className="editor-subtitle">TOKEN MAP <span>LEXER TOKEN → GRAMMAR TERMINAL</span></div><div className="map-list">{(f.rules||[]).filter(r=>!r.skip&&r.name).map(r=><label key={r.name}><span>{r.name}</span><i>→</i><input className="mono-input" value={(f.tokenMap||{})[r.name]||''} placeholder="terminal" onChange={e=>update('tokenMap',{...(f.tokenMap||{}),[r.name]:e.target.value})}/></label>)}</div></details>{!f.source&&<div className="input-field"><label>TERMINAL STRING <span>USED WHEN NO SOURCE PROGRAM IS GIVEN</span></label><div className="input-line"><input value={f.input||''} onChange={e=>update('input',e.target.value)} onKeyDown={e=>e.key==='Enter'&&onRun()}/><button onClick={()=>onRun()} aria-label="Run"><Play size={14} fill="currentColor"/></button></div></div>}</>}
 {page==='slr'&&<div className="mode-toggle"><span>METHOD</span>{[['slr','SLR(1)'],['lalr','LALR(1)'],['lr1','Canonical LR(1)']].map(([m,l])=><button key={m} className={(f.method||'slr')===m?'on':''} onClick={()=>{update('method',m);onRun({method:m})}}>{l}</button>)}</div>}{(page==='ll1'||page==='slr')&&<div className="input-field"><label>INPUT STRING <span>SPACES OPTIONAL · e.g. id+id*id</span></label><div className="input-line"><input value={f.input||''} onChange={e=>update('input',e.target.value)} onKeyDown={e=>e.key==='Enter'&&onRun()}/><button onClick={()=>onRun()} aria-label="Run parse"><Play size={14} fill="currentColor"/></button></div></div>}
 {page==='automata'&&<div className="input-field"><label>TRY A STRING <span>LIVE DFA ACCEPTANCE CHECK</span></label><div className="input-line"><input placeholder="e.g. aababb" value={f.probe||''} onChange={e=>update('probe',e.target.value)}/></div></div>}
 <div className="editor-foot"><span className={`syntax-state ${syntax?.state||"idle"}`} title={syntax?.msg||""}><span className="tiny-green"/> {syntax?.state==="busy"?"CHECKING…":syntax?.state==="bad"?`ERROR · ${syntax.msg}`:syntax?.state==="ok"?"SYNTAX OK":"READY"}</span><span>CTRL ↵ <button onClick={()=>onRun()}>Run analysis</button></span></div></div>
}
function Output({page,data,picked,setPicked,step,setStep,probe,grammarText,onApply}){
 if(!data)return null;
 if(page==='lexer')return <LexerOutput data={data} picked={picked} setPicked={setPicked}/>;
 if(page==='automata')return <AutomataOutput data={data} step={step} setStep={setStep} probe={probe}/>;
 if(page==='timemachine')return <TimeOutput data={data} step={step} setStep={setStep}/>;
 if(page==='grammar')return <GrammarOutput data={data} grammarText={grammarText} onApply={onApply}/>;
 return <ParserOutput page={page} data={data} step={step} setStep={setStep} onApply={onApply} grammarText={grammarText}/>;
}
function describeError(d){const e=d.errors?.[0];if(e)return `${e.line?`LINE ${e.line}: `:''}${e.message}`;if(d.ruleErrors?.length)return d.ruleErrors[0].message;if(typeof d.error==='string')return d.error;if(d.error?.message)return `${d.error.message}${d.error.position!=null?` (position ${d.error.position})`:''}`;return 'Check the input.'}
function OutputHeader({label,meta,ok}){const st=ok==='warn'?'warn':ok?'good':'bad';return <div className="result-head"><div><span className="section-mark">{label}</span><span className={`result-status ${st}`}><i/>{st==='warn'?'COMPUTED · WITH NOTES':st==='good'?'COMPUTED':'ISSUES FOUND'}</span></div><small>{meta}</small></div>}
function LexerOutput({data,picked,setPicked}){return <div className="result-section"><OutputHeader label="TOKEN STREAM" meta={`${data.stats?.tokens||0} TOKENS · ${data.stats?.errors||0} ERRORS`} ok={data.valid}/><div className="source-preview"><div className="source-preview-bar"><span>SOURCE MAP</span><span>SELECT A TOKEN TO INSPECT</span></div><div className="source-text">{data.spans?.map((s,i)=><span key={i} className={`${s.kind==='error'?'source-error':s.kind==='token'?'source-token':''} ${data.tokens?.find(t=>t.id===s.tokenId)?.id===picked?'selected':''}`} onClick={()=>s.tokenId!==undefined&&setPicked(s.tokenId)}>{data.source.slice(s.start,s.end)}</span>)}</div></div><div className="table-scroll"><table className="data-table"><thead><tr><th>#</th><th>TYPE</th><th>LEXEME</th><th>LINE</th><th>COLUMN</th></tr></thead><tbody>{data.tokens?.map(t=><tr onClick={()=>setPicked(t.id)} className={picked===t.id?'selected-row':''} key={t.id}><td>{String(t.id+1).padStart(2,'0')}</td><td><span className="token-badge">{t.type}</span></td><td className="mono">{JSON.stringify(t.lexeme)}</td><td>{t.line}</td><td>{t.column}</td></tr>)}</tbody></table></div>{data.errors?.length>0&&<div className="diagnostic-list">{data.errors.map((e,i)=><div key={i}><b>LEXICAL ERROR</b><span>{e.message||`Unexpected ${e.char} at ${e.line}:${e.column}`}</span></div>)}</div>}</div>}
const showSym=s=>s===' '?'␣':s==='\n'?'\\n':s==='\t'?'\\t':s==='\r'?'\\r':s;
// ['a','b',...,'z','_'] -> "_,a-z": runs of 3+ consecutive characters become ranges.
function compactSymbols(syms){
 const uniq=[...new Set(syms)];const special=uniq.filter(c=>c.length!==1);const chars=uniq.filter(c=>c.length===1).sort((a,b)=>a.charCodeAt(0)-b.charCodeAt(0));
 const parts=[];for(let i=0;i<chars.length;){let j=i;while(j+1<chars.length&&chars[j+1].charCodeAt(0)===chars[j].charCodeAt(0)+1)j++;if(j-i>=2)parts.push(`${showSym(chars[i])}-${showSym(chars[j])}`);else for(let k=i;k<=j;k++)parts.push(showSym(chars[k]));i=j+1}
 const all=[...parts,...special.map(showSym)];return all.length>6?`${all.slice(0,5).join(',')},… (${uniq.length})`:all.join(',')}
function runMachine(m,text){let current=m?.start,ok=true;const path=[current];for(const ch of text||''){const edge=m.transitions.find(t=>t.from===current&&t.symbol===ch)||(ch!=='\n'&&m.transitions.find(t=>t.from===current&&t.symbol==='Σ'));if(!edge){ok=false;break}current=edge.to;path.push(current)}const st=m?.states.find(s=>s.id===current);return {accepted:ok&&!!st?.accepting,current:ok?current:null,path,stuck:!ok}}
function AutomataOutput({data,step,setStep,probe}){
 const [view,setView]=useState('dfa');
 if(!data.valid)return <div className="result-section"><OutputHeader label="DETERMINISTIC AUTOMATON" meta="PATTERN ERROR" ok={false}/><div className="diagnostic-list"><div><b>POSITION {data.error?.position??'—'}</b><span>{data.error?.message||'The expression could not be parsed.'}</span></div></div></div>;
 const nfa={states:data.nfa.states.map(s=>({id:`q${s.id}`,accepting:s.accepting,start:s.id===data.nfa.start})),transitions:data.nfa.states.flatMap(s=>[...s.transitions.map(t=>({from:`q${s.id}`,symbol:t.symbol,to:`q${t.to}`})),...s.epsilon.map(t=>({from:`q${s.id}`,symbol:'ε',to:`q${t}`}))])};
 const machine=view==='min'?data.minDfa:data.dfa;
 const graph=view==='nfa'?nfa:machine;
 const steps=view==='min'?(data.minDfa?.steps||[]):(data.subsetSteps||[]);
 const s=Math.min(step,Math.max(steps.length-1,0));
 const res=runMachine(machine,probe);
 const highlight=new Set(view==='nfa'?[]:probe?res.path:(view==='dfa'&&steps[s]?.state?[steps[s].state,steps[s].to].filter(Boolean):[]));
 // Edges actually traversed, keyed "from|to", with the 1-based step(s) that used each one.
 const hotEdges=new Map();
 if(view!=='nfa'){
  if(probe){res.path.slice(1).forEach((to,i)=>{const k=`${res.path[i]}|${to}`;if(!hotEdges.has(k))hotEdges.set(k,[]);hotEdges.get(k).push(i+1)})}
  else if(view==='dfa'&&steps[s]?.state&&steps[s]?.to)hotEdges.set(`${steps[s].state}|${steps[s].to}`,[]);
 }
 const stuckAt=probe&&view!=='nfa'&&res.stuck?res.path[res.path.length-1]:null;
 const alphabet=machine.alphabet||[];
 return <div className="result-section"><OutputHeader label="FINITE AUTOMATA" meta={`${data.stats.nfaStates} NFA → ${data.stats.dfaStates} DFA → ${data.stats.minDfaStates} MINIMAL STATES`} ok={data.valid}/>
  <div className="view-toggle">{[['nfa',`Thompson NFA · ${data.stats.nfaStates}`],['dfa',`Subset DFA · ${data.stats.dfaStates}`],['min',`Minimal DFA · ${data.stats.minDfaStates}`]].map(([k,l])=><button key={k} className={view===k?'on':''} onClick={()=>{setView(k);setStep(0)}}>{l}</button>)}<span className="ast-chip" title="Parsed structure">AST <code>{data.ast}</code></span></div>
  {view!=='nfa'&&<><div className="automata-toolbar"><span>{view==='min'?'PARTITION REFINEMENT':'SUBSET CONSTRUCTION'} <i>·</i> STEP {s+1} / {steps.length}</span><div><button onClick={()=>setStep(Math.max(0,s-1))}>←</button><button onClick={()=>setStep(Math.min(steps.length-1,s+1))}>→</button></div></div><div className="step-explanation">{steps[s]?.explanation}{view==='min'&&steps[s]?.partition&&<div className="partition">{steps[s].partition.map((b,i)=><span key={i}>{'{'+b.join(', ')+'}'}</span>)}</div>}</div></>}
  {view==='nfa'&&<div className="step-explanation">Thompson's construction built {data.stats.nfaStates} states and {data.stats.nfaEdges} edges, {data.stats.epsilonEdges} of them ε-moves. Each operator contributes a small fragment with one entry and one exit.</div>}
  <AutomataGraph states={graph.states} transitions={graph.transitions} highlight={highlight} hotEdges={hotEdges} stuck={stuckAt} end={probe&&view!=='nfa'?res.current:null}/>
  {view==='nfa'?<div className="table-scroll"><table className="data-table"><thead><tr><th>STATE</th><th>ε-CLOSURE</th><th>ACCEPTING</th></tr></thead><tbody>{data.nfa.epsilonClosures.map(c=><tr key={c.state}><td className="mono">q{c.state}{c.state===data.nfa.start?' →':''}</td><td className="mono">{'{'+c.closure.map(n=>'q'+n).join(', ')+'}'}</td><td>{data.nfa.accepting.includes(c.state)?'YES':'—'}</td></tr>)}</tbody></table></div>
  :<div className="table-scroll"><table className="data-table"><thead><tr><th>STATE</th><th>{view==='min'?'MERGES':'NFA SUBSET'}</th><th>ACCEPT</th>{alphabet.map(a=><th key={a}>{showSym(a)}</th>)}</tr></thead><tbody>{machine.states.map(st=><tr key={st.id} className={highlight.has(st.id)?'selected-row':''}><td className="mono">{st.id}{st.start?' →':''}</td><td className="mono">{view==='min'?(st.dfaStates||[]).join(' '):(st.nfaStates||[]).map(n=>`q${n}`).join(' ')}</td><td>{st.accepting?'YES':'—'}</td>{alphabet.map(a=><td className="mono" key={a}>{machine.transitions.find(t=>t.from===st.id&&t.symbol===a)?.to||'—'}</td>)}</tr>)}</tbody></table></div>}
  {probe!==undefined&&view!=='nfa'&&<div className="probe-result"><span>STRING TEST</span><code>{probe||'ε'}</code><b className={res.accepted?'':'rejected'}>{res.accepted?'ACCEPTED':'REJECTED'}</b><small>{res.stuck?`No transition after ${res.path.join(' → ')}`:`Path ${res.path.join(' → ')}${res.accepted?' ends in an accepting state':' ends in a non-accepting state'}`}</small></div>}
 </div>}

function layoutAutomaton(states,transitions,R,minGap=0){
 // Layered left-to-right layout: column = BFS distance from the start state.
 const ids=states.map(s=>s.id),start=(states.find(s=>s.start)||states[0])?.id;
 const out={};for(const t of transitions)(out[t.from]??=[]).push(t.to);
 const depth={};if(start!=null){depth[start]=0;const q=[start];while(q.length){const a=q.shift();for(const b of out[a]||[])if(!(b in depth)){depth[b]=depth[a]+1;q.push(b)}}}
 let maxD=Math.max(0,...Object.values(depth));for(const id of ids)if(!(id in depth))depth[id]=++maxD;
 const cols=[];for(const id of ids)(cols[depth[id]]??=[]).push(id);
 const colGap=Math.max(2*R+62,ids.length>18?92:118,minGap),rowGap=2*R+58;
 const tallest=Math.max(...cols.map(c=>c?.length||0));
 const pos={};cols.forEach((col,ci)=>(col||[]).forEach((id,ri)=>{pos[id]={x:ci*colGap,y:(ri-(col.length-1)/2)*rowGap}}));
 return {pos,width:(cols.length-1)*colGap,height:(tallest-1)*rowGap};
}
function AutomataGraph({states,transitions,highlight=new Set(),hotEdges=new Map(),stuck=null,end}){
 if(!states?.length)return null;
 const R=22;
 const labelChars=(()=>{const g={};for(const t of transitions)(g[`${t.from}|${t.to}`]??=[]).push(t.symbol);return Math.max(0,...Object.entries(g).filter(([k])=>{const [a,b]=k.split('|');return a!==b}).map(([k,v])=>compactSymbols(v).length+(hotEdges.has(k)?2+hotEdges.get(k).join(',').length:0)))})();
 const {pos,width:lw,height:lh}=layoutAutomaton(states,transitions,R,Math.min(2*R+labelChars*7.6+22,260));
 const pairs={};for(const t of transitions){if(!(t.from in pos)||!(t.to in pos))continue;const k=`${t.from}|${t.to}`;(pairs[k]??={from:t.from,to:t.to,symbols:[]}).symbols.push(t.symbol)}
 const list=Object.values(pairs);
 const label=syms=>compactSymbols(syms);
 // Geometry for every edge: quadratic curves that bend away from reverse edges and from nodes in the way.
 const nodesList=Object.entries(pos);
 const geo=list.map((p,i)=>{const a=pos[p.from],b=pos[p.to];
  if(p.from===p.to){const above=nodesList.some(([id,c])=>id!==p.from&&Math.abs(c.x-a.x)<R&&c.y<a.y)||list.some(q=>q.from!==q.to&&((q.from===p.from&&pos[q.to].y<a.y&&Math.abs(pos[q.to].x-a.x)<R)||(q.to===p.from&&pos[q.from].y<a.y&&Math.abs(pos[q.from].x-a.x)<R)));return {p,loop:true,a,dir:above?1:-1}}
  const dx=b.x-a.x,dy=b.y-a.y,len=Math.hypot(dx,dy)||1,nx=-dy/len,ny=dx/len;
  let bend=0;
  if(pairs[`${p.to}|${p.from}`])bend=26;
  else{const blocked=nodesList.some(([id,c])=>{if(id===p.from||id===p.to)return false;const t=((c.x-a.x)*dx+(c.y-a.y)*dy)/(len*len);if(t<=0||t>=1)return false;return Math.hypot(a.x+t*dx-c.x,a.y+t*dy-c.y)<R+10});if(blocked)bend=Math.min(30+len*0.38,230)*(dx>=0?1:-1)}
  const cx=(a.x+b.x)/2+nx*bend,cy=(a.y+b.y)/2+ny*bend;
  const u=(fx,fy,tx,ty)=>{const l=Math.hypot(tx-fx,ty-fy)||1;return [(tx-fx)/l,(ty-fy)/l]};
  const [ux,uy]=u(a.x,a.y,cx,cy),[vx,vy]=u(b.x,b.y,cx,cy);
  const sx=a.x+ux*R,sy=a.y+uy*R,ex=b.x+vx*(R+3),ey=b.y+vy*(R+3);
  return {p,sx,sy,cx,cy,ex,ey,lx:0.25*sx+0.5*cx+0.25*ex,ly:0.25*sy+0.5*cy+0.25*ey}});
 let minX=-R-34,maxX=lw+R+10,minY=-lh/2-R-50,maxY=lh/2+R+(geo.some(g=>g.loop&&g.dir>0)?56:14);
 for(const g of geo)if(!g.loop){minX=Math.min(minX,g.lx-30);maxX=Math.max(maxX,g.lx+30);minY=Math.min(minY,g.ly-16);maxY=Math.max(maxY,g.ly+16)}
 const pad=14,W=maxX-minX+pad*2,H=maxY-minY+pad*2,ox=pad-minX,oy=pad-minY;
 return <div className="automata-graph-scroll"><svg className="automata-graph" width={W} height={H} viewBox={`0 0 ${W} ${H}`} role="img" aria-label="State transition graph"><defs>
  <marker id="ag-arrow" viewBox="0 0 10 10" markerUnits="userSpaceOnUse" markerWidth="11" markerHeight="11" refX="9" refY="5" orient="auto-start-reverse"><path className="mk" d="M0,1 L10,5 L0,9 z"/></marker>
  <marker id="ag-arrow-eps" viewBox="0 0 10 10" markerUnits="userSpaceOnUse" markerWidth="11" markerHeight="11" refX="9" refY="5" orient="auto-start-reverse"><path className="mk eps" d="M0,1 L10,5 L0,9 z"/></marker>
  <marker id="ag-arrow-hot" viewBox="0 0 10 10" markerUnits="userSpaceOnUse" markerWidth="11" markerHeight="11" refX="9" refY="5" orient="auto-start-reverse"><path className="mk hot" d="M0,1 L10,5 L0,9 z"/></marker></defs>
  <g transform={`translate(${ox},${oy})`}>
  {[...geo].sort((x,y)=>hotEdges.has(`${x.p.from}|${x.p.to}`)-hotEdges.has(`${y.p.from}|${y.p.to}`)).map((g,i)=>{const order=hotEdges.get(`${g.p.from}|${g.p.to}`);const hot=!!order;const eps=g.p.symbols.every(s=>s==='ε');const cls=`ag-edge ${hot?'hot':eps?'eps':''}`;const mk=hot?'url(#ag-arrow-hot)':eps?'url(#ag-arrow-eps)':'url(#ag-arrow)';const txt=label(g.p.symbols);
   if(g.loop){const {x,y}=g.a,d=g.dir;return <g key={i} className={cls}><path d={`M ${x-11} ${y+d*(R-3)} C ${x-30} ${y+d*(R+40)}, ${x+30} ${y+d*(R+40)}, ${x+11} ${y+d*(R-3)}`} fill="none" markerEnd={mk}/><text className="ag-label" x={x} y={d<0?y-R-34:y+R+42} textAnchor="middle">{txt}{order?.length>0&&<tspan className="ag-order" dx="5">{`#${order.join(",")}`}</tspan>}</text></g>}
   return <g key={i} className={cls}><path d={`M ${g.sx} ${g.sy} Q ${g.cx} ${g.cy} ${g.ex} ${g.ey}`} fill="none" markerEnd={mk}/><text className="ag-label" x={g.lx} y={g.ly+4} textAnchor="middle">{txt}{order?.length>0&&<tspan className="ag-order" dx="5">{`#${order.join(",")}`}</tspan>}</text></g>})}
  {states.map(s=>{const {x,y}=pos[s.id];const isEnd=s.id===end,on=highlight.has(s.id),isStuck=s.id===stuck;return <g key={s.id} className={`ag-node ${s.accepting?'accept':''} ${on?'on':''} ${isEnd?'end':''} ${isStuck?'stuck':''}`}>{isStuck&&<circle className="stuck-ring" cx={x} cy={y} r={R+6}/>}
   {s.start&&<path className="ag-start" d={`M ${x-R-30} ${y} L ${x-R-3} ${y}`} markerEnd="url(#ag-arrow-hot)"/>}
   <circle cx={x} cy={y} r={R}/>{s.accepting&&<circle className="ring" cx={x} cy={y} r={R-5}/>}
   <text x={x} y={y+4.5} textAnchor="middle">{s.id}</text></g>})}
  </g></svg>
  <div className="ag-legend"><span><i className="lg-start"/>start</span><span><i className="lg-accept"/>accepting</span>{transitions.some(t=>t.symbol==='ε')&&<span><i className="lg-eps"/>ε-move</span>}{transitions.some(t=>t.symbol==='Σ')&&<span><b>Σ</b> any other character</span>}{hotEdges.size>0&&<span><i className="lg-hot"/>{[...hotEdges.values()].some(v=>v.length)?"path taken (#n = step)":"this construction step"}</span>}{stuck&&<span><i className="lg-stuck"/>no transition: string rejected here</span>}</div>
 </div>}
function GrammarOutput({data,grammarText,onApply}){
 const [tx,setTx]=useState(null),[busyT,setBusyT]=useState('');
 const [sentence,setSentence]=useState(''),[der,setDer]=useState(null),[derBusy,setDerBusy]=useState(false),[samples,setSamples]=useState([]);
 useEffect(()=>{setTx(null);setDer(null);const sm=data.samples||[];setSamples(sm);if(sm.length){const len=x=>x.split(' ').filter(Boolean).length;const s=sm.find(x=>len(x)>=3&&len(x)<=9)??[...sm].sort((a,b)=>len(a)-len(b))[Math.min(1,sm.length-1)];setSentence(s);derive(s)}},[data]);
 async function transform(kind){setBusyT(kind);try{const r=await request(kind==='lr'?'/grammar/left-recursion':'/grammar/factor',{grammar:grammarText||''});setTx({kind,...r})}catch(e){setTx({kind,valid:false,errors:[{message:e.message}]})}finally{setBusyT('')}}
 async function derive(s=sentence){if(!String(s).trim()){setDer({empty:true});return}setDerBusy(true);try{setDer(await request('/lr/analyze',{grammar:grammarText||'',input:s,method:'lr1'}))}catch(e){setDer({valid:false,errors:[{message:e.message}]})}finally{setDerBusy(false)}}
 async function more(){try{const r=await request('/grammar/samples',{grammar:grammarText||'',seed:Math.floor(Math.random()*1e6)});if(r.samples?.length){setSamples(r.samples);const len=x=>x.split(' ').filter(Boolean).length;const s=r.samples.find(x=>len(x)>=3&&len(x)<=12)??r.samples[r.samples.length-1];setSentence(s);derive(s)}}catch{}}
 const g=data.grammar||{};
 if(!data.valid)return <div className="result-section"><OutputHeader label="GRAMMAR ANALYSIS" meta="SYNTAX ERROR" ok={false}/><Errors data={data}/><p className="muted-line">Each line needs the form <code>A -&gt; x y | z</code>. See Field notes for the full notation.</p></div>;
 const issues=data.issues||[];
 const nullable=Object.entries(data.nullable||{}).filter(([,v])=>v).map(([k])=>k);
 const hasLR=issues.some(i=>i.kind==='left-recursion'),hasLF=issues.some(i=>i.kind==='factoring');
 const hasErr=issues.some(i=>i.severity==='error'),hasWarn=issues.some(i=>i.severity==='warning')||(data.warnings||[]).length>0;
 const txSteps=tx?.valid?(tx.kind==='lr'?tx.steps.map(s=>({text:s.explanation,after:s.after})):tx.transformations.map(t=>({text:`Factor the common prefix "${t.prefix.join(' ')}" out of ${t.alternatives} alternatives of ${t.lhs} into the new non-terminal ${t.newNonterminal}.`}))):[];
 const sim=der?.simulation;
 return <div className="result-section"><OutputHeader label="GRAMMAR ANALYSIS" meta={`${g.productions?.length||0} PRODUCTIONS · ${g.nonterminals?.length||0} NONTERMINALS`} ok={hasErr?false:hasWarn?'warn':true}/>
  {data.classes?.valid&&<ClassStrip classes={data.classes} current={null}/>}
  <div className="set-grid"><SetColumn title="FIRST" values={data.first}/><SetColumn title="FOLLOW" values={data.follow}/></div>
  <div className="grammar-stats"><div><small>START SYMBOL</small><b>{g.start}</b></div><div><small>NULLABLE</small><b>{nullable.join(' · ')||'none'}</b></div><div><small>TERMINALS</small><b>{(g.terminals||[]).join(' · ')}</b></div></div>
  <div className="diagnostic-list">{issues.map((x,i)=><div key={i} className={`issue-${x.severity}`}><b>{x.affects?`BLOCKS ${x.affects.join(', ')}`:String(x.severity||'note').toUpperCase()}</b><span><strong>{x.title}.</strong> {x.detail}{x.symbols?.length>0&&<em> Involves: {x.symbols.join(', ')}.</em>}{x.opportunities&&<em> {x.opportunities.map(o=>o.detail).join(' ')}</em>}</span></div>)}{(data.warnings||[]).map((w,i)=><div key={'w'+i} className="issue-warning"><b>LINE {w.line}</b><span>{w.message}</span></div>)}</div>
  <div className="transform-bar"><span>TRANSFORM</span><button className={hasLR?'suggested':''} disabled={!!busyT} onClick={()=>transform('lr')}>{busyT==='lr'?'Working…':'Eliminate left recursion'}</button><button className={hasLF?'suggested':''} disabled={!!busyT} onClick={()=>transform('lf')}>{busyT==='lf'?'Working…':'Left factor'}</button></div>
  {tx&&<div className="transform-result">{!tx.valid?<Errors data={tx}/>:!tx.changed?<p className="muted-line">No change needed. The grammar has no {tx.kind==='lr'?'left recursion this algorithm removes':'common prefixes'}.</p>:<><ol>{txSteps.map((s,i)=><li key={i}>{s.text}{s.after&&<pre>{s.after}</pre>}</li>)}</ol>{(tx.warnings||[]).map((w,i)=><p className="muted-line" key={i}>⚠ {w}</p>)}<div className="tx-final"><small>RESULTING GRAMMAR</small><pre>{tx.text}</pre><button className="button primary" onClick={()=>onApply(tx.text)}>Apply to editor</button></div></>}</div>}
  <div className="derive-panel"><div className="derive-head"><span>DERIVE A SENTENCE</span><small>CHECKED WITH CANONICAL LR(1), THE MOST GENERAL PARSER HERE</small></div>
   <div className="input-line derive-input"><input value={sentence} onChange={e=>setSentence(e.target.value)} onKeyDown={e=>e.key==='Enter'&&derive()} placeholder="type a sentence, e.g. id + id * id" aria-label="Sentence to derive"/><button onClick={()=>derive()} aria-label="Derive"><Play size={14} fill="currentColor"/></button></div>
   {samples.length>0&&<div className="derive-samples"><small>GENERATED FROM THIS GRAMMAR</small>{samples.map(s=><button key={s} className={s===sentence?'on':''} onClick={()=>{setSentence(s);derive(s)}} title={s||'ε'}>{s||'ε'}</button>)}<button className="shuffle" onClick={more} title="Generate other random sentences"><Sparkles size={11}/> more</button></div>}
   {derBusy&&<p className="muted-line">Deriving…</p>}
   {!derBusy&&der&&(der.empty?<p className="muted-line">{samples.includes('')?'ε, the empty string, is in this language.':'Type a sentence made of the grammar’s terminals.'}</p>
    :!der.valid?<Errors data={der}/>
    :der.tokenError?<div className="diagnostic-list"><div><b>INPUT</b><span>{der.tokenError}</span></div></div>
    :!der.deterministic?<div className="diagnostic-list"><div className="issue-warning"><b>PROBABLY AMBIGUOUS</b><span>This grammar is not LR(1) ({der.conflicts.length} conflict{der.conflicts.length!==1?'s':''}), so no deterministic one-token-lookahead parser can choose a single derivation. A sentence may have more than one parse tree. Try an unambiguous version, e.g. the precedence-layered E / T / F grammar.</span></div></div>
    :sim&&<><div className="parse-summary"><div><span className={`accept-stamp ${sim.accepted?'':'reject'}`}>{sim.accepted?'DERIVABLE':'NOT IN LANGUAGE'}</span><span>{sim.accepted?`“${sentence}” is a sentence of this grammar, derived in ${sim.derivations.leftmost.rules.length} steps.`:sim.error}</span></div></div>{sim.accepted&&<><Derivations d={sim.derivations} open/><TreeDiagram tree={sim.tree} name="derivation-tree"/></>}</>)}
  </div>
  <details className="trace-details"><summary>How FIRST and FOLLOW were computed ({(data.firstSteps||[]).length+(data.followSteps||[]).length} steps) <ChevronDown size={14}/></summary><div className="reason-list"><small>NULLABLE</small>{(data.nullableSteps||[]).map((s,i)=><p key={'n'+i}><i>round {s.round}</i>{s.reason}</p>)}<small>FIRST</small>{(data.firstSteps||[]).map((s,i)=><p key={'f'+i}><i>round {s.round}</i>{s.reason}</p>)}<small>FOLLOW</small>{(data.followSteps||[]).map((s,i)=><p key={'o'+i}><i>round {s.round}</i>{s.reason}</p>)}</div></details>
 </div>}
function SetColumn({title,values}){return <div className="set-column"><div>{title}<small>TERMINAL SETS</small></div>{Object.entries(values||{}).map(([k,v])=><div className="set-row" key={k}><b>{k}</b><span>{`{ ${(Array.isArray(v)?v:[]).join(', ')} }`}</span></div>)}</div>}
function ParserOutput({page,data,step,setStep}){
 const sim=data.simulation,table=data.table,g=data.grammar||{};
 const method=page==='ll1'?'ll1':(data.method||'slr');
 const label={ll1:'LL(1)',slr:'SLR(1)',lalr:'LALR(1)',lr1:'LR(1)'}[method];
 const states=page==='slr'?(data.automaton?.states||[]):[];
 const steps=sim?.steps||[];const s=Math.min(step,Math.max(steps.length-1,0));const cur=steps[s];
 const title=page==='ll1'?'PREDICTIVE TABLE':method==='slr'?'LR(0) AUTOMATON & SLR TABLE':method==='lalr'?'LALR(1) AUTOMATON & TABLE':'CANONICAL LR(1) AUTOMATON & TABLE';
 if(!data.valid)return <div className="result-section"><OutputHeader label={title} meta="GRAMMAR ERROR" ok={false}/><Errors data={data}/></div>;
 const actionName=a=>typeof a==='string'?a:a?.type;
 let stackText='';if(cur){if(page==='slr'){const parts=[String(cur.stateStack[0])];cur.symbolStack.forEach((sym,i)=>parts.push(sym,String(cur.stateStack[i+1])));stackText=parts.join(' ')}else stackText=[...(cur.stack||[])].reverse().map(x=>x.symbol).join(' ')}
 const ok=page==='ll1'?data.isLL1:(data.deterministic??data.isSLR);
 const meta=page==='ll1'?`${table?.rows?.length||0} ROWS · ${(data.conflicts||[]).length} CONFLICTS`:`${states.length} STATES${method==='lalr'&&data.stats?.lr1States?` (MERGED FROM ${data.stats.lr1States} LR(1))`:''} · ${(data.conflicts||[]).length} CONFLICTS`;
 return <div className="result-section"><OutputHeader label={title} meta={meta} ok={ok}/>
  {data.classes?.valid&&<ClassStrip classes={data.classes} current={method}/>}
  <div className="parse-summary"><div><span className={`accept-stamp ${sim?.accepted?'':'reject'}`}>{sim?.accepted?'ACCEPTED':sim&&sim.canParse!==false?'REJECTED':data.tokenError?'BAD INPUT':ok?'READY':'NOT '+label}</span><span>{data.tokenError||sim?.error||sim?.reason||`${label} table built from this grammar.`}</span></div><span>{sim?.steps?.length?`${steps.length} OPERATIONS`:`${data.conflicts?.length||0} CONFLICTS`}</span></div>
  {(data.conflicts||[]).length>0&&<div className="diagnostic-list">{data.conflicts.map((c,i)=><div key={i}><b>{page==='ll1'?`M[${c.nonterminal}, ${c.terminal}]`:`I${c.state} · ${c.type}`}</b><span>{c.reason}{c.items&&<em> Items: {c.items.join('  |  ')}</em>}{page==='ll1'&&(data.issues||[]).some(x=>x.kind==='left-recursion')&&<em> Tip: the grammar is left-recursive; open the Grammar workbench and use “Eliminate left recursion”.</em>}</span></div>)}</div>}
  <div className="prod-legend"><small>PRODUCTIONS</small>{(g.productions||[]).map(p=><span key={p.index} className={cur?.production?.index===p.index?'on':''}><i>{page==='ll1'?'p':'r'}{p.index+1}</i>{p.text}</span>)}</div>
  {page==='slr'&&<div className="state-grid">{states.map(st=><div className={`lr-state ${cur&&(cur.state===st.id||cur.stateStack?.at(-1)===st.id)?'current':''} ${(data.conflicts||[]).some(c=>c.state===st.id)?'conflict':''}`} key={st.id}><b>I{st.id}{st.mergedFrom?.length>1&&<small className="merged" title="LALR merged these canonical LR(1) states">= {st.mergedFrom.join(' + ')}</small>}</b><div>{st.items?.map((it,i)=><code key={i} className={it.complete?'complete':''}>{it.text}</code>)}</div></div>)}</div>}
  {table&&<div className="table-scroll"><TableRenderer page={page} table={table} active={cur?.tableCell} grammar={g}/></div>}
  {sim&&steps.length>0&&<><Stepper label="PARSE TRACE" step={s} length={steps.length} setStep={setStep}/><div className="active-step"><span className="step-index">{String(s+1).padStart(2,'0')}</span><div><b className={`act-${actionName(cur?.action)}`}>{String(actionName(cur?.action)||'action').toUpperCase()}</b><p>{cur?.explanation}</p></div></div><div className="trace-rail">{steps.map((x,i)=><button key={i} className={`${i===s?'current':''} act-${actionName(x.action)}`} onClick={()=>setStep(i)} title={actionName(x.action)}>{i+1}</button>)}</div><div className="parse-state"><div><small>{page==='slr'?'STACK (STATES AND SYMBOLS)':'STACK (TOP ON THE RIGHT)'}</small><code>{stackText||'—'}</code></div><div><small>INPUT REMAINING</small><code>{(cur?.input||[]).join(' ')||'$'}</code></div></div>{sim.tree&&<><TreeDiagram tree={sim.tree} step={s} active={new Set([...(cur?.created||[]),cur?.nodeId].filter(v=>v!=null))} name={`parse-tree-${method}`}/><Derivations d={sim.accepted?sim.derivations:null}/></>}</>}
 </div>}

function TreeDiagram({tree,step:traceStep=Infinity,active:traceActive=new Set(),name='parse-tree'}){
 const [note,setNote]=useState('');
 const [grow,setGrowState]=useState(()=>{try{return localStorage.getItem('parselab-tree-grow')==='1'}catch{return false}});
 const setGrow=v=>{setGrowState(v);try{localStorage.setItem('parselab-tree-grow',v?'1':'0')}catch{}};
 const traced=traceStep!==Infinity;
 const step=traced&&grow?traceStep:Infinity;
 const active=traced?traceActive:new Set();
 const lay=useMemo(()=>tree?layoutTree(tree):null,[tree]);
 if(!tree)return null;
 const flash=m=>{setNote(m);setTimeout(()=>setNote(''),2200)};
 const save=(blob,file)=>{const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=file;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(a.href),1000)};
 const svgOut=()=>save(new Blob([treeToSvg(tree)],{type:'image/svg+xml'}),`${name}.svg`);
 const pngOut=()=>{const svg=treeToSvg(tree);const img=new Image();img.onload=()=>{const c=document.createElement('canvas');c.width=img.width*2;c.height=img.height*2;const ctx=c.getContext('2d');ctx.scale(2,2);ctx.drawImage(img,0,0);c.toBlob(b=>b&&save(b,`${name}.png`))};img.src='data:image/svg+xml;charset=utf-8,'+encodeURIComponent(svg)};
 const texOut=async()=>{const tex=treeToLatex(tree);try{await navigator.clipboard.writeText(tex);flash('LaTeX copied (needs \\usepackage{qtree})')}catch{save(new Blob([tex],{type:'text/plain'}),`${name}.tex`)}};
 const pending=n=>(n.eps?(n.parentExpanded??n.createdStep):n.createdStep)>step;
 const built=lay.nodes.filter(n=>!pending(n)).length;
 const {px,py,W,H}=lay;
 return <div className="tree-wrap"><div className="tree-heading">PARSE TREE <small>{step===Infinity?`${lay.nodes.length} NODES${traced?' · HIGHLIGHT FOLLOWS THE TRACE':''}`:`${built} OF ${lay.nodes.length} NODES BUILT`}</small><span className="tree-export">{traced&&<span className="seg" role="group" aria-label="Tree display"><button className={!grow?'on':''} onClick={()=>setGrow(false)} title="Show the whole tree">Full tree</button><button className={grow?'on':''} onClick={()=>setGrow(true)} title="Only show nodes built so far">Grow with steps</button></span>}{note&&<em>{note}</em>}<button onClick={svgOut} title="Download the complete tree as SVG"><Download size={11}/> SVG</button><button onClick={pngOut} title="Download the complete tree as PNG"><Download size={11}/> PNG</button><button onClick={texOut} title="Copy as LaTeX qtree for a report">LaTeX</button></span></div>
  <div className="tree-canvas"><svg className="tree-svg" width={W} height={H} viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Parse tree">
   {lay.edges.map(([a,b],i)=>{const my=(py(a.depth)+py(b.depth))/2;return <path key={i} className={`te ${pending(b)?'pending':''}`} d={`M ${px(a.x)} ${py(a.depth)+14} C ${px(a.x)} ${my}, ${px(b.x)} ${my}, ${px(b.x)} ${py(b.depth)-14}`} fill="none"/>})}
   {lay.nodes.map((n,i)=>{const w=lay.boxW(n);const cls=`tn ${n.terminal?'term':'nt'} ${n.eps?'eps':''} ${pending(n)?'pending':''} ${n.id!=null&&active.has(n.id)?'hot':''} ${n.terminal&&!n.eps&&n.matchedStep!=null&&n.matchedStep<=step?'matched':''}`;return <g key={i} className={cls}><title>{n.productionText||n.label}</title><rect x={px(n.x)-w/2} y={py(n.depth)-14} width={w} height="28" rx={n.terminal?14:5}/><text x={px(n.x)} y={py(n.depth)+4.5} textAnchor="middle">{n.label}</text></g>})}
  </svg></div>
  <div className="ag-legend"><span><i className="lg-nt"/>non-terminal</span><span><i className="lg-t"/>terminal</span>{traced&&<span><i className="lg-hot"/>changed at this step</span>}{step!==Infinity&&<span><i className="lg-pend"/>not built yet</span>}</div>
 </div>}

function TableRenderer({page,table,active,grammar}){
 const ptext=i=>grammar?.productions?.[i]?.text||'';
 if(page==='ll1'){const rows=table.rows||[],ts=table.columns||[];return <table className="data-table"><thead><tr><th>NONTERMINAL</th>{ts.map(t=><th key={t}>{t}</th>)}</tr></thead><tbody>{rows.map(r=><tr key={r.nonterminal}><td className="mono">{r.nonterminal}</td>{r.cells.map(c=>{const on=active&&active.nonterminal===r.nonterminal&&active.terminal===c.column;return <td title={c.production!==null?`${c.productions.map(ptext).join('  /  ')}\n${c.reason||''}`:'error entry'} className={`${c.production!==null?(c.conflict?'conflict-cell':'filled-cell'):''} ${on?'active-cell':''}`} key={c.column}>{c.production!==null?c.productions.map(p=>`p${p+1}`).join(' / '):'—'}</td>})}</tr>)}</tbody></table>}
 const rows=table.rows||[],terminals=table.terminals||[],gotos=rows[0]?.gotos?.map(x=>x.column)||[];
 const code=a=>a.type==='shift'?`s${a.target}`:a.type==='reduce'?`r${a.production+1}`:'acc';
 return <table className="data-table"><thead><tr><th rowSpan="2">STATE</th><th colSpan={terminals.length}>ACTION</th><th colSpan={gotos.length}>GOTO</th></tr><tr>{terminals.map(x=><th key={x}>{x}</th>)}{gotos.map(x=><th key={x}>{x}</th>)}</tr></thead><tbody>{rows.map(r=><tr key={r.state}><td className="mono">{r.state}</td>{r.cells.map(c=>{const on=active&&active.state===r.state&&active.terminal===c.column;return <td key={c.column} title={(c.actions||[]).map(a=>a.reason).join('\n')} className={`${c.conflict?'conflict-cell':c.action?'filled-cell':''} ${on?'active-cell':''}`}>{c.actions?.length?c.actions.map(code).join(' / '):'—'}</td>})}{r.gotos.map(c=><td className={c.target!==null?'filled-cell':''} key={c.column}>{c.target??'—'}</td>)}</tr>)}</tbody></table>}
function TimeOutput({data,step,setStep}){
 const steps=data.steps||[],stages=data.stages||[];const s=Math.min(step,Math.max(steps.length-1,0));const cur=steps[s];const stage=cur?.stage;
 if(!steps.length)return <div className="result-section"><OutputHeader label="SYNCHRONIZED EXECUTION TRACE" meta="NOT STARTED" ok={false}/><Errors data={data}/></div>;
 let treeStep=-1;for(let i=s;i>=0;i--){if(steps[i].parseStep!=null){treeStep=steps[i].parseStep;break}}if(stage==='result')treeStep=Infinity;
 const range=cur?.sourceRange;const src=data.source||'';
 let stackText='';if(cur?.stateStack){stackText=cur.stateStack.join(' ')}else if(cur?.stack){stackText=[...cur.stack].reverse().map(x=>x.symbol).join(' ')}
 return <div className="result-section"><OutputHeader label="SYNCHRONIZED EXECUTION TRACE" meta={`${steps.length} EVENTS · ${(data.mode||'ll')==='slr'?'SLR(1)':'LL(1)'} PARSER`} ok={data.accepted}/>
  {data.error&&!data.accepted&&<div className="diagnostic-list"><div><b>{data.valid===false?'HALTED':'REJECTED'}</b><span>{typeof data.error==='string'?data.error:data.error?.message}</span></div></div>}
  <div className="stage-track">{stages.map(st=><div className={stage===st.id?'on':''} key={st.id}><i/>{st.label||st.id}<small>{st.count??steps.filter(x=>x.stage===st.id).length} EVENTS</small></div>)}</div>
  <Stepper label="COMPILER TIME MACHINE" step={s} length={steps.length} setStep={setStep} frame/>
  <input className="timeline-range" type="range" min="0" max={Math.max(steps.length-1,0)} value={s} onChange={e=>setStep(Number(e.target.value))} aria-label="Timeline"/>
  {src&&<div className="source-preview"><div className="source-preview-bar"><span>SOURCE</span><span>{range?`CHARACTERS ${range.start}–${range.end}`:'—'}</span></div><div className="source-text">{range&&range.end-range.start<src.length?<>{src.slice(0,range.start)}<mark>{src.slice(range.start,range.end)}</mark>{src.slice(range.end)}</>:src}</div></div>}
  {(data.tokens||[]).length>0&&<div className="token-strip">{data.tokens.map((t,i)=><span key={i} className={cur?.tokenIndex===i&&(stage==='parse'||stage==='tree'||stage==='lex')?'on':''}><b>{t.symbol}</b>{t.lexeme!==t.symbol&&<small>{t.lexeme}</small>}</span>)}<span className="eof">$</span></div>}
  {cur&&<div className={`time-card sev-${cur.severity}`}><div className="time-card-top"><span>{String(cur.stage||'EVENT').toUpperCase()}</span><span>{cur.index+1} / {steps.length}</span></div><h3>{cur.title||'Transformation'}</h3><p>{cur.detail}</p><small><b>Why:</b> {cur.why}</small>{cur.next&&<small><b>Next:</b> {cur.next}</small>}</div>}
  {(stackText||cur?.input)&&stage==='parse'&&<div className="parse-state"><div><small>{cur.stateStack?'STATE STACK':'STACK (TOP ON THE RIGHT)'}</small><code>{stackText||'—'}</code></div><div><small>INPUT REMAINING</small><code>{Array.isArray(cur.input)?cur.input.map(x=>typeof x==='object'?x.symbol:x).join(' '):'—'}</code></div></div>}
  <div className="trace-rail">{steps.map((x,i)=><button key={i} className={`${i===s?'current':''} stage-${x.stage} sev-${x.severity}`} onClick={()=>setStep(i)} title={`${x.stage}: ${x.title}`}>{i+1}</button>)}</div>
  {data.tree&&<TreeDiagram tree={data.tree} step={treeStep} active={new Set([...(cur?.created||[]),cur?.nodeId].filter(v=>v!=null))}/>}
  <Derivations d={data.accepted?data.derivations:null}/>
 </div>}
function Errors({data}){const list=data.errors?.length?data.errors:data.error?[{message:typeof data.error==='string'?data.error:data.error.message}]:[];return <div className="diagnostic-list">{list.map((e,i)=><div key={i}><b>{e.line?`LINE ${e.line}`:'ERROR'}</b><span>{e.message}</span></div>)}</div>}
function Inspector({page,data,busy,navigate}){let facts={lexer:['MAXIMAL MUNCH','At each source position, the longest matching rule wins. Rule order breaks ties.','Source positions are one based. Skipped rules advance the scanner but do not enter the output stream.'],automata:['THOMPSON → SUBSETS → MINIMAL','Each expression operator contributes a local NFA fragment. Epsilon closure turns sets of NFA states into DFA states, and partition refinement merges states no input can tell apart.','The wildcard Σ stands for any character except newline that is not named elsewhere in the alphabet.'],grammar:['FIXED POINT ANALYSIS','FIRST and FOLLOW are computed by repeatedly applying production rules until no set changes.','Nullable symbols can pass FIRST information through a production prefix.'],ll1:['PREDICTIVE DECISION','A table cell uses FIRST(rhs), and FOLLOW(lhs) when the right side can derive epsilon.','More than one production in a cell means the grammar is not LL(1).'],slr:['BOTTOM-UP EVIDENCE','Item sets describe what the parser may recognize. SLR(1) reduces on all of FOLLOW(A); LALR(1) and canonical LR(1) carry a precise lookahead in every item, so they accept strictly more grammars.','Conflicting ACTION entries indicate this grammar is not SLR(1).'],timemachine:['ONE COMPUTED HISTORY','The timeline is assembled from the lexer and parser’s actual execution steps.','Move backward or forward to inspect each transformation and rule.']}[page]||[];return <><div className="inspector-title"><span>FIELD NOTES</span><BookOpen size={15}/></div>{busy?<div className="inspector-loading"><span className="spinner"/> Computing result…</div>:<><div className="inspector-note"><div className="note-index">01 / CONCEPT</div><h3>{facts[0]}</h3><p>{facts[1]}</p></div>{data&&<div className="inspector-note result-note"><div className="note-index">02 / THIS RUN</div><h3 className={data.valid===false?'bad':''}>{data.valid===false?'Needs attention':page==='lexer'?`${data.stats?.tokens||0} tokens found`:page==='automata'?`${data.stats?.dfaStates||0} DFA → ${data.stats?.minDfaStates||0} minimal states`:page==='grammar'?((data.issues||[]).some(i=>i.severity==='error')?'Grammar has errors':(data.issues||[]).some(i=>i.kind==='left-recursion')?'Valid · not LL(1) as written':'Valid grammar'):page==='timemachine'?(data.accepted?'Program accepted':`${data.steps?.length||0} trace events`):page==='ll1'?(data.isLL1?'Grammar is LL(1)':'Grammar is not LL(1)'):page==='slr'?`Grammar is ${(data.deterministic??data.isSLR)?'':'not '}${{slr:'SLR(1)',lalr:'LALR(1)',lr1:'LR(1)'}[data.method||'slr']}`:'Table generated'}</h3><p>{data.valid===false?data.errors?.[0]?.message||(typeof data.error==='string'?data.error:data.error?.message):'Results below come from the current input and the compiler engine.'}</p></div>}<div className="inspector-tip"><Sparkles size={14}/><p>Try changing one part of the input and run it again. The updated trace shows which decisions depend on that change.</p></div><div className="inspector-links"><span>QUICK REFERENCE</span><button onClick={()=>navigate('docs')}>Grammar syntax <ArrowRight size={13}/></button><button onClick={()=>navigate('docs')}>Regex operators <ArrowRight size={13}/></button><button onClick={()=>navigate('docs')}>Keyboard shortcuts <ArrowRight size={13}/></button></div></>}</>}
function Examples({examples,onExample}){const [filter,setFilter]=useState('all');const kinds=['all',...new Set(examples.map(e=>e.kind))];return <div className="examples-page"><div className="page-heading"><div><div className="eyebrow">PARSELAB / 08 <span className="eyebrow-line"/> EXPERIMENT LIBRARY</div><h1>Experiments</h1><p>Small, focused investigations. Load one into a workbench and make it your own.</p></div><div className="example-count">{examples.length}<small>READY TO RUN</small></div></div><div className="filter-row">{kinds.map(k=><button className={filter===k?'chosen':''} onClick={()=>setFilter(k)} key={k}>{k.toUpperCase()}</button>)}<span><Search size={14}/> {examples.filter(e=>filter==='all'||e.kind===filter).length} experiments</span></div><div className="example-grid">{examples.filter(e=>filter==='all'||e.kind===filter).map((e,i)=><button className="example-card" key={e.id} onClick={()=>onExample(e)}><div className="example-card-top"><span>{e.kicker}</span><span className="difficulty">{e.difficulty}</span></div><div className="example-illustration"><span>{e.kind==='regex'?'ε → ◉':e.kind==='lexer'?'ID · NUM · OP':e.kind==='timemachine'?'SOURCE → TREE':e.kind==='slr'?'I₀ → Iₙ':'FIRST / FOLLOW'}</span><i/></div><h3>{e.title}</h3><p>{e.description}</p><div className="tag-row">{e.tags?.map(t=><span key={t}>{t}</span>)}</div><div className="example-open">Load experiment <ArrowRight size={14}/></div></button>)}</div></div>}
function Docs(){return <div className="docs-page"><div className="eyebrow">PARSELAB / FIELD NOTES</div><h1>A pocket guide<br/>to the front end.</h1><p className="docs-lede">ParseLab makes compiler construction inspectable. Start with a stage, change an input, then trace the evidence that led to each result.</p><div className="docs-columns">{[['01','Lexical analysis','Token rules are regular expressions. The scanner applies maximal munch: it selects the longest match at the current source position. Rule order settles equal length matches.'],['02','Automata','Thompson construction creates an epsilon NFA from a regular expression. Subset construction groups NFA states into a deterministic machine.'],['03','Grammar analysis','FIRST describes what can begin a derivation. FOLLOW describes what can appear after a nonterminal. Nullable symbols let both sets propagate through a production.'],['04','LL(1)','A top down parser uses one lookahead token and one table entry to expand a nonterminal. Multiple entries in one cell mean a predictive choice is ambiguous.'],['05','SLR, LALR and LR(1)','A bottom up parser shifts tokens into states and reduces recognized right sides. SLR places reductions with FOLLOW sets; canonical LR(1) tracks one lookahead per item; LALR(1) merges LR(1) states with equal cores, which is what yacc and bison build. The class strip shows which parsers accept your grammar.'],['06','Time machine','The signature view combines actual tokenization and parser steps into one navigable trace, so an acceptance or rejection has an inspectable history.']].map(x=><article key={x[0]}><small>{x[0]} / CONCEPT</small><h3>{x[1]}</h3><p>{x[2]}</p></article>)}</div><div className="docs-note"><FileCode2 size={18}/><span><b>Grammar notation</b>Use one production per line: <code>E -&gt; E + T | T</code>, or put each alternative on its own line starting with <code>|</code>. Arrows <code>-&gt;</code>, <code>→</code>, <code>::=</code> and <code>:=</code> all work. Use <code>ε</code> (or <code>eps</code>) for the empty production, <code>%start S</code> to choose a start symbol, and <code>//</code> or <code>#</code> for comments. Upper-case left sides are non-terminals; every other symbol is a terminal.</span></div><div className="docs-ref"><article><small>REGEX OPERATORS</small><table className="data-table"><tbody>{[['ab','concatenation'],['a|b','alternation'],['a*  a+  a?','zero or more · one or more · optional'],['( )','grouping'],['[a-z0-9_]','character class with ranges'],['[^"]','negated class (includes tab and newline)'],['.','any character except newline'],['\d  \w  \s','digit · word character · whitespace'],['\n  \t  \+','escapes'],['ε','empty string']].map(r=><tr key={r[0]}><td className="mono">{r[0]}</td><td>{r[1]}</td></tr>)}</tbody></table></article><article><small>KEYBOARD</small><table className="data-table"><tbody>{[['Ctrl / ⌘ + Enter','run the current bench'],['← / →','previous / next trace step'],['Space','play or pause a trace'],['Enter in an input','run with the new input']].map(r=><tr key={r[0]}><td className="mono">{r[0]}</td><td>{r[1]}</td></tr>)}</tbody></table></article><article><small>GRAMMAR TRANSFORMS</small><p>The Grammar workbench can <b>eliminate left recursion</b> (direct and indirect, Dragon Book Algorithm 4.19) and <b>left factor</b> common prefixes. Each step is explained, and the result can be applied to the editor and then sent to the LL(1) studio.</p></article></div></div>}

function Stepper({label,step,length,setStep,frame}){
 const [playing,setPlaying]=useState(false);
 useEffect(()=>{if(!playing)return;if(step>=length-1){setPlaying(false);return}const t=setTimeout(()=>setStep(step+1),650);return()=>clearTimeout(t)},[playing,step,length]);
 useEffect(()=>{const onKey=e=>{const tag=(e.target.tagName||'').toLowerCase();if(tag==='input'||tag==='textarea'||e.ctrlKey||e.metaKey)return;if(e.key==='ArrowRight'){setStep(Math.min(length-1,step+1))}else if(e.key==='ArrowLeft'){setStep(Math.max(0,step-1))}else if(e.key===' '){e.preventDefault();setPlaying(p=>!p)}};window.addEventListener('keydown',onKey);return()=>window.removeEventListener('keydown',onKey)},[step,length]);
 return <div className="trace-controls"><div><span>{label}</span><b>{frame?'FRAME':'STEP'} {String(step+1).padStart(2,'0')} <i>/ {length}</i></b></div><div><button onClick={()=>setStep(0)} title="First step">⏮</button><button onClick={()=>setStep(Math.max(0,step-1))} title="Previous (←)">←</button><button className="play" onClick={()=>{if(step>=length-1)setStep(0);setPlaying(p=>!p)}} title="Play / pause (space)">{playing?'❚❚':'▶'}</button><button onClick={()=>setStep(Math.min(length-1,step+1))} title="Next (→)">→</button><button onClick={()=>setStep(length-1)} title="Last step">⏭</button></div></div>}

function Derivations({d,open=false}){if(!d||!d.leftmost?.forms?.length)return null;return <details className="trace-details" open={open}><summary>Leftmost and rightmost derivations ({d.leftmost.rules.length} steps) <ChevronDown size={14}/></summary><div className="deriv-grid">{[['leftmost','LEFTMOST ⇒lm'],['rightmost','RIGHTMOST ⇒rm']].map(([k,l])=><div key={k}><small>{l}</small><ol>{(d[k]?.forms||[]).map((f,i)=><li key={i}><code>{i?'⇒ ':'  '}{f}</code>{i>0&&<em>{d[k].rules[i-1]?.productionText}</em>}</li>)}</ol></div>)}</div></details>}

function ClassStrip({classes,current}){return <div className="class-strip"><div className="class-cells">{classes.classes.map(c=><div key={c.id} className={`${c.ok?'yes':c.ok===false?'no':'na'} ${c.id===current?'current':''}`}><small>{c.label}</small><b>{c.ok?'✓':c.ok===false?'✗':'—'}</b><span>{c.states!=null?`${c.states} states`:'table'}{c.conflicts?` · ${c.conflicts} conflict${c.conflicts>1?'s':''}`:''}</span></div>)}</div><p>{classes.verdict}</p></div>}

function treeToSvg(tree){
 const {nodes,edges,W,H,px,py,boxW}=layoutTree(tree);
 const esc=t=>String(t).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
 const edge=([a,b])=>{const my=(py(a.depth)+py(b.depth))/2;return `<path d="M ${px(a.x)} ${py(a.depth)+14} C ${px(a.x)} ${my}, ${px(b.x)} ${my}, ${px(b.x)} ${py(b.depth)-14}" fill="none" stroke="#8d8b7e" stroke-width="1.4"/>`};
 const box=n=>{const w=boxW(n);return `<g><rect x="${px(n.x)-w/2}" y="${py(n.depth)-14}" width="${w}" height="28" rx="${n.terminal?14:5}" fill="${n.terminal?'#ffffff':'#e6ebcf'}" stroke="${n.terminal?'#6f7064':'#7d8a45'}" stroke-width="1.4"/><text x="${px(n.x)}" y="${py(n.depth)+4.5}" text-anchor="middle" font-family="DM Mono, Consolas, monospace" font-size="13" font-weight="${n.terminal?400:600}" fill="${n.eps?'#8a897f':n.terminal?'#2f302a':'#3a4220'}"${n.eps?' font-style="italic"':''}>${esc(n.label)}</text></g>`};
 return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}"><rect width="100%" height="100%" fill="#ffffff"/>${edges.map(edge).join('')}${nodes.map(box).join('')}</svg>`}

function treeToLatex(tree){
 const esc=t=>String(t).replace(/\\/g,'\\textbackslash{}').replace(/([#$%&_{}])/g,'\\$1').replace(/~/g,'\\textasciitilde{}').replace(/\^/g,'\\textasciicircum{}').replace(/ε/g,'$\\varepsilon$');
 const go=n=>{const kids=n.children||[];if(!kids.length)return n.terminal?esc(n.symbol):n.productionIndex!=null?`[.${esc(n.symbol)} $\\varepsilon$ ]`:esc(n.symbol);return `[.${esc(n.symbol)} ${kids.map(go).join(' ')} ]`};
 return `% Parse tree exported from ParseLab. Requires \\usepackage{qtree}\n\\Tree ${go(tree)}\n`}

function readShare(){try{const m=/^#\/([a-z0-9]+)(?:\?d=([A-Za-z0-9_-]+))?/.exec(location.hash||'');if(!m)return {};const page=modules.some(x=>x.id===m[1])?m[1]:null;let data=null;if(m[2]){const b64=m[2].replace(/-/g,'+').replace(/_/g,'/');const bin=atob(b64+'='.repeat((4-b64.length%4)%4));data=JSON.parse(new TextDecoder().decode(Uint8Array.from(bin,c=>c.charCodeAt(0))))}return {page,data}}catch{return {}}}

function shareUrl(page,data){const bytes=new TextEncoder().encode(JSON.stringify(data||{}));let bin='';bytes.forEach(b=>bin+=String.fromCharCode(b));const b64=btoa(bin).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');return `${location.origin}${location.pathname}#/${page}?d=${b64}`}

function layoutTree(tree,opts={}){
 const nodes=[],edges=[];let leaf=0,maxDepth=0;
 const longest=n=>Math.max(String(n.symbol).length,...(n.children||[]).map(longest));
 const slot=Math.max(opts.slot||52,longest(tree)*8+26),row=opts.row||68,pad=opts.pad??22;
 const walk=(n,depth)=>{maxDepth=Math.max(maxDepth,depth);const kids=(n.children||[]).map(c=>walk(c,depth+1));let x;
  if(kids.length)x=(kids[0].x+kids[kids.length-1].x)/2;else x=leaf++;
  const me={id:n.id,label:n.symbol,terminal:n.terminal,x,depth,createdStep:n.createdStep,matchedStep:n.matchedStep,productionText:n.productionText};nodes.push(me);kids.forEach(k=>edges.push([me,k]));
  if(!kids.length&&!n.terminal&&n.productionIndex!=null){const e={label:'ε',terminal:true,eps:true,x,depth:depth+1,createdStep:n.createdStep,parentExpanded:n.expandedStep??n.createdStep};maxDepth=Math.max(maxDepth,depth+1);nodes.push(e);edges.push([me,e])}
  return me};
 walk(tree,0);
 const W=Math.max(leaf,1)*slot+pad*2,H=(maxDepth+1)*row+pad*2-row+28;
 return {nodes,edges,W,H,px:x=>pad+x*slot+slot/2,py:d=>pad+14+d*row,boxW:n=>Math.max(30,String(n.label).length*8+18)};
}

function ThemeToggle(){
 const read=()=>{try{return localStorage.getItem('parselab-theme')||'system'}catch{return 'system'}};
 const [pref,setPref]=useState(read);
 useEffect(()=>{
  const mq=window.matchMedia?.('(prefers-color-scheme: dark)');
  const apply=()=>{const dark=pref==='dark'||(pref==='system'&&!!mq?.matches);document.documentElement.setAttribute('data-theme',dark?'dark':'light')};
  apply();try{localStorage.setItem('parselab-theme',pref)}catch{}
  if(pref!=='system'||!mq)return;mq.addEventListener?.('change',apply);return()=>mq.removeEventListener?.('change',apply);
 },[pref]);
 const opts=[['light',Sun,'Light'],['system',Monitor,'System default'],['dark',Moon,'Dark']];
 return <div className="theme-toggle" role="radiogroup" aria-label="Color theme">{opts.map(([v,Icon,label])=><button key={v} role="radio" aria-checked={pref===v} className={pref===v?'on':''} onClick={()=>setPref(v)} title={`${label} theme`} aria-label={`${label} theme`}><Icon size={14}/></button>)}</div>}

const HERO_GRAMMAR="E  -> T E'\nE' -> + T E' | - T E' | ε\nT  -> F T'\nT' -> * F T' | / F T' | ε\nF  -> ( E ) | id | num";
const HERO_RULES=[{name:'ID',pattern:'[a-zA-Z_][a-zA-Z0-9_]*'},{name:'NUM',pattern:'[0-9]+(\\.[0-9]+)?'},{name:'PLUS',pattern:'\\+'},{name:'MINUS',pattern:'-'},{name:'STAR',pattern:'\\*'},{name:'SLASH',pattern:'/'},{name:'LPAREN',pattern:'\\('},{name:'RPAREN',pattern:'\\)'},{name:'WS',pattern:'[ \\t]+',skip:true}];
const HERO_MAP={ID:'id',NUM:'num',PLUS:'+',MINUS:'-',STAR:'*',SLASH:'/',LPAREN:'(',RPAREN:')'};
const HERO_SAMPLES=[['price + tax * rate','precedence'],['(a + b) * 2','parentheses'],['total / (n - 1.5)','numbers'],['x * (y + z','missing )'],['a + @ b','bad character']];
const HERO_STAGES=[['scan','SCAN','maximal munch'],['tokens','TOKENS','lexer output'],['parse','PARSE','LL(1) stack'],['tree','TREE','parse tree']];
function LivePipeline({health,onOpen,src:srcProp,setSrc:setSrcProp,onResult}){
 const [srcLocal,setSrcLocal]=useState(HERO_SAMPLES[0][0]);
 const src=srcProp??srcLocal,setSrc=setSrcProp??setSrcLocal;
 const [res,setRes]=useState(null),[busy,setBusy]=useState(false),[ms,setMs]=useState(null);
 const [stage,setStage]=useState(0),[tick,setTick]=useState(0),[paused,setPaused]=useState(false),[hold,setHold]=useState(false);
 const reduced=useMemo(()=>{try{return window.matchMedia('(prefers-reduced-motion: reduce)').matches}catch{return false}},[]);
 const seq=useRef(0),cardRef=useRef(null);
 // Run the real engine (debounced) whenever the expression changes.
 useEffect(()=>{if(!health)return;const id=++seq.current;setBusy(true);const t=setTimeout(async()=>{const t0=performance.now();try{const r=await request('/timemachine',{grammar:HERO_GRAMMAR,source:src,rules:HERO_RULES,tokenMap:HERO_MAP,mode:'ll'});if(id!==seq.current)return;setRes(r);setMs(performance.now()-t0);setStage(0);setTick(0);setHold(false)}catch{if(id===seq.current)setRes(null)}finally{if(id===seq.current)setBusy(false)}},320);return()=>clearTimeout(t)},[src,health]);
 useEffect(()=>{onResult?.(res)},[res]);
 const tokens=res?.lexer?.tokens||[],lexErrors=res?.lexer?.errors||[];
 const parseSteps=(res?.steps||[]).filter(s=>s.stage==='parse');
 const lay=useMemo(()=>res?.tree?layoutTree(res.tree,{row:44,slot:44,pad:6}):null,[res]);
 const treeOrder=useMemo(()=>lay?[...lay.nodes].map((n,i)=>({n,i})).sort((a,b)=>((a.n.eps?a.n.parentExpanded:a.n.createdStep)??0)-((b.n.eps?b.n.parentExpanded:b.n.createdStep)??0)||a.n.depth-b.n.depth).map(x=>x.i):[],[lay]);
 const lexBlocked=lexErrors.length>0;
 const scanItems=[...tokens.map(t=>({kind:'tok',...t})),...lexErrors.map(e=>({kind:'err',...e}))].sort((a,b)=>a.start-b.start);
 const lengths=[Math.max(scanItems.length*5,1)+8,18,lexBlocked?12:Math.max(parseSteps.length*2,1)+10,lay?treeOrder.length+14:12];
 // Animation clock: ~9 frames per second, advancing through the four stages.
 const atEnd=tick>=lengths[stage];
 useEffect(()=>{if(reduced||paused||!res||(hold&&atEnd))return;const t=setInterval(()=>setTick(k=>k+1),110);return()=>clearInterval(t)},[reduced,paused,res,hold,atEnd]);
 useEffect(()=>{if(!hold&&tick>=lengths[stage]){setStage(s=>(s+1)%4);setTick(0)}},[tick,stage,hold]);
 const frame=reduced?Infinity:tick;
 const pick=i=>{setStage(i);setTick(0);setHold(true);setPaused(false)};
 const onMove=e=>{const el=cardRef.current;if(!el)return;const r=el.getBoundingClientRect();el.style.setProperty('--mx',`${e.clientX-r.left}px`);el.style.setProperty('--my',`${e.clientY-r.top}px`)};
 const accepted=!!res?.accepted;
 const status=!health?'offline':busy&&!res?'running':!res?'idle':accepted?'accepted':'rejected';
 const errText=typeof res?.error==='string'?res.error:res?.error?.message;

 let body=null;
 if(!health)body=<div className="pipeline-empty">Start the ParseLab engine to run this pipeline live.<small>uvicorn app.main:app --app-dir backend --port 8001</small></div>;
 else if(!res)body=<div className="pipeline-empty">Compiling…</div>;
 else if(stage===0){
  const k=Math.min(Math.floor(frame/5),scanItems.length-1),cur=scanItems[k];
  body=<div className="pipeline-scan">
   <div className="pipeline-chars">{[...src].map((ch,i)=>{const it=scanItems.findIndex(x=>i>=x.start&&i<x.end);const done=it>=0&&it<k,on=it===k;const err=it>=0&&scanItems[it].kind==='err'&&it<=k;return <span key={i} className={`${done?'done':''} ${on?'on':''} ${err?'err':''} ${ch===' '?'sp':''}`}>{ch===' '?'\u00a0':ch}</span>})}{cur&&<i className="pipeline-caret" style={{left:`${cur.end}ch`}}/>}</div>
   {cur?<div className={`pipeline-scanline ${cur.kind}`}>{cur.kind==='tok'?<><b>{cur.type}</b><span>matched <code>{JSON.stringify(cur.lexeme)}</code> · {cur.lexeme.length} char{cur.lexeme.length!==1?'s':''}</span><small>DFA {cur.path.join(' → ')} {(cur.candidates||[]).filter(c=>c.length>0).length>1?`· beat ${(cur.candidates||[]).filter(c=>c.length>0&&c.rule!==cur.type).map(c=>`${c.rule} (${c.length})`).join(', ')}`:'· only rule that matches'}</small></>:<><b>ERROR</b><span>{cur.message}</span><small>line {cur.line}, column {cur.column}</small></>}</div>:<div className="pipeline-scanline">Empty input.</div>}
   <div className="pipeline-progress"><i style={{width:`${scanItems.length?Math.min(100,((k+1)/scanItems.length)*100):0}%`}}/></div>
  </div>;
 }else if(stage===1){
  body=<div className="pipeline-tokens">
   <div className="pipeline-chiprow">{tokens.map((t,i)=><span key={`${src}-${i}`} className="pipeline-chip" style={{animationDelay:`${reduced?0:i*90}ms`}}><b>{t.type}</b><small>{t.lexeme}</small></span>)}{lexErrors.map((e,i)=><span key={'e'+i} className="pipeline-chip err"><b>ERROR</b><small>{e.char}</small></span>)}</div>
   <div className="pipeline-stream"><small>TERMINAL STREAM FOR THE PARSER</small><code>{tokens.map(t=>HERO_MAP[t.type]||'?').join(' ')} <i>$</i></code></div>
  </div>;
 }else if(stage===2){
  if(lexBlocked)body=<div className="pipeline-empty err">Parsing skipped: the lexer could not tokenize the input.<small>{errText}</small></div>;
  else{const k=Math.min(Math.floor(frame/2),parseSteps.length-1),st=parseSteps[k]||{};const stack=[...(st.stack||[])].reverse();const input=(st.input||[]).map(x=>typeof x==='object'?x.symbol:x);
   body=<div className="pipeline-parse">
    <div className="pipeline-row"><small>STACK</small><div className="pipeline-stack">{stack.map((x,i)=><span key={i} className={i===stack.length-1?'top':''}>{x.symbol}</span>)}</div></div>
    <div className="pipeline-row"><small>INPUT</small><div className="pipeline-stack input">{input.map((x,i)=><span key={i} className={i===0?'top':''}>{x}</span>)}</div></div>
    <div className={`pipeline-action ${st.severity==='error'?'err':''}`}><b>{st.title||'—'}</b><span>{st.detail}</span></div>
    <div className="pipeline-progress"><i style={{width:`${parseSteps.length?((k+1)/parseSteps.length)*100:0}%`}}/></div>
   </div>}
 }else{
  if(!lay)body=<div className="pipeline-empty err">No parse tree: {errText||'the input was rejected.'}</div>;
  else{const shown=new Set(treeOrder.slice(0,Math.max(1,frame)));const latest=treeOrder[Math.min(frame,treeOrder.length)-1];
   body=<div className="pipeline-tree"><svg viewBox={`0 0 ${lay.W} ${lay.H}`} preserveAspectRatio="xMidYMid meet" role="img" aria-label="Parse tree">
    {lay.edges.map(([a,b],i)=>{const bi=lay.nodes.indexOf(b);if(!shown.has(bi))return null;const my=(lay.py(a.depth)+lay.py(b.depth))/2;return <path key={i} d={`M ${lay.px(a.x)} ${lay.py(a.depth)+14} C ${lay.px(a.x)} ${my}, ${lay.px(b.x)} ${my}, ${lay.px(b.x)} ${lay.py(b.depth)-14}`} className="pipeline-tedge"/>})}
    {lay.nodes.map((n,i)=>{if(!shown.has(i))return null;const w=lay.boxW(n);return <g key={i} className={`pipeline-tnode ${n.terminal?'term':'nt'} ${n.eps?'eps':''} ${i===latest?'new':''}`}><rect x={lay.px(n.x)-w/2} y={lay.py(n.depth)-14} width={w} height="28" rx={n.terminal?14:5}/><text x={lay.px(n.x)} y={lay.py(n.depth)+5} textAnchor="middle">{n.label}</text></g>})}
   </svg>{!accepted&&<div className="pipeline-treenote">Partial tree: {errText}</div>}</div>}
 }

 return <div ref={cardRef} className={`pipeline pipeline-live status-${status}`} onMouseMove={onMove} >
  <div className="pipeline-top"><span>LIVE PIPELINE / {stage+1} OF 4{hold?' · HOLD':paused?' · PAUSED':''}</span><span className={`pipeline-running ${status}`}><i/>{status==='offline'?'ENGINE OFFLINE':busy?'COMPILING…':status==='accepted'?'ACCEPTED':status==='rejected'?'REJECTED':'READY'}</span></div>
  <div className="pipeline-source"><small>TYPE AN EXPRESSION <span>· the real engine lexes and parses it</span></small>
   <input className="pipeline-input" value={src} spellCheck="false" maxLength={60} aria-label="Expression to compile" onChange={e=>setSrc(e.target.value)} onFocus={()=>setPaused(false)}/>
   <div className="pipeline-samples">{HERO_SAMPLES.map(([s,l])=><button key={s} className={src===s?'on':''} onClick={()=>{setSrc(s);setPaused(false)}} title={s}>{l}</button>)}</div>
  </div>
  <div className="pipeline-tabs" role="tablist">{HERO_STAGES.map(([id,label,sub],i)=><button key={id} role="tab" aria-selected={stage===i} className={`${stage===i?'on':''} ${i<stage?'past':''}`} onClick={()=>pick(i)}><span>0{i+1}</span><b>{label}</b><small>{sub}</small>{stage===i&&!reduced&&<i style={{width:`${Math.min(100,(tick/lengths[i])*100)}%`}}/>}</button>)}</div>
  <div className="pipeline-body" key={`${stage}-${res?.steps?.length||0}`}>{body}</div>
  <div className="pipeline-bottom"><span>{res?`${tokens.length} TOKENS · ${parseSteps.length} PARSE STEPS${lay?` · ${lay.nodes.length} NODES`:''}${ms!=null?` · ${Math.round(ms)} MS`:''}`:'CHARACTERS → STRUCTURE'}</span><span className="pipeline-actions">{!reduced&&<button onClick={()=>{if(paused||hold){setPaused(false);setHold(false);if(hold&&atEnd){setStage(s=>(s+1)%4);setTick(0)}}else setPaused(true)}} title={paused||hold?'Play all four stages':'Pause the animation'}>{paused||hold?'▶ PLAY ALL':'❚❚ PAUSE'}</button>}<button onClick={()=>onOpen(src)} disabled={!health} title="Open this expression in the Time machine">FULL TRACE →</button></span></div>
 </div>}

const JOURNEY=[['source','Source','Raw characters'],['tokens','Tokens','Lexical units'],['automata','Automata','State transitions'],['grammar','Grammar','Language structure'],['tree','Parse tree','A proven sentence']];
function Journey({live,src,health,onOpen}){
 const [tab,setTab]=useState(0),[hoverChar,setHoverChar]=useState(null),[hoverTok,setHoverTok]=useState(null),[pickTok,setPickTok]=useState(0),[dfas,setDfas]=useState({}),[gram,setGram]=useState(null),[focusNt,setFocusNt]=useState(null);
 const tokens=live?.lexer?.tokens||[],lexErrors=live?.lexer?.errors||[];
 const tree=live?.tree;
 const lay=useMemo(()=>tree?layoutTree(tree):null,[tree]);
 const used=useMemo(()=>{const m={};const walk=n=>{if(!n)return;if(n.productionText)m[n.productionText]=(m[n.productionText]||0)+1;(n.children||[]).forEach(walk)};walk(tree);return m},[tree]);
 useEffect(()=>{if(health&&!gram)request('/grammar/analyze',{grammar:HERO_GRAMMAR}).then(setGram).catch(()=>{})},[health]);
 const tok=tokens[Math.min(pickTok,Math.max(tokens.length-1,0))];
 const rule=tok&&HERO_RULES.find(r=>r.name===tok.type);
 useEffect(()=>{if(!health||!rule||dfas[rule.pattern])return;request('/regex/analyze',{pattern:rule.pattern}).then(r=>setDfas(d=>({...d,[rule.pattern]:r}))).catch(()=>{})},[health,rule?.pattern]);
 useEffect(()=>{setPickTok(p=>Math.min(p,Math.max(tokens.length-1,0)))},[tokens.length]);
 const counts=[`${src.length} chars`,`${tokens.length} token${tokens.length!==1?'s':''}`,`${new Set(tokens.map(t=>t.type)).size} DFAs used`,`${Object.keys(used).length} rules used`,lay?`${lay.nodes.length} nodes`:'no tree'];
 const tokAt=i=>tokens.findIndex(t=>i>=t.start&&i<t.end);
 let panel;
 if(!health)panel=<div className="journey-empty">Start the engine to follow an input through the compiler.</div>;
 else if(!live)panel=<div className="journey-empty">Compiling “{src}”…</div>;
 else if(tab===0){const hc=hoverChar,ti=hc!=null?tokAt(hc):-1;
  panel=<div className="jp-source"><div className="jp-chars" onMouseLeave={()=>setHoverChar(null)}>{[...src].map((ch,i)=>{const t=tokAt(i);const err=lexErrors.some(e=>i>=e.start&&i<e.end);return <button key={i} className={`${t>=0?`tok t${t%2}`:'ws'} ${err?'err':''} ${hc===i?'on':''} ${ti>=0&&t===ti?'same':''}`} onMouseEnter={()=>setHoverChar(i)} onFocus={()=>setHoverChar(i)}><b>{ch===' '?'·':ch}</b><small>{i}</small></button>})}</div>
   <p className="jp-info">{hc==null?'Hover a character: the lexer sees only a stream of characters with offsets. Spaces (·) belong to no token.':<>offset <b>{hc}</b> · line 1, column <b>{hc+1}</b> · {lexErrors.some(e=>hc>=e.start&&hc<e.end)?<span className="bad">no rule can match this character</span>:ti>=0?<>part of <b>{tokens[ti].type}</b> “{tokens[ti].lexeme}” (characters {tokens[ti].start}–{tokens[ti].end-1})</>:'whitespace, skipped by the WS rule'}</>}</p></div>}
 else if(tab===1){panel=<div className="jp-tokens"><div className="jp-mini">{[...src].map((ch,i)=>{const t=tokAt(i);return <span key={i} className={hoverTok!=null&&t===hoverTok?'on':''}>{ch}</span>})}</div>
   <div className="table-scroll"><table className="data-table"><thead><tr><th>#</th><th>TYPE</th><th>LEXEME</th><th>COLUMN</th><th>TERMINAL</th><th>WHY</th></tr></thead><tbody>{tokens.map((t,i)=><tr key={i} className={hoverTok===i?'selected-row':''} onMouseEnter={()=>setHoverTok(i)} onMouseLeave={()=>setHoverTok(null)}><td>{i+1}</td><td><span className="token-badge">{t.type}</span></td><td className="mono">{t.lexeme}</td><td>{t.column}</td><td className="mono">{HERO_MAP[t.type]}</td><td className="jp-why">{t.explanation.split('. ').slice(-1)[0]}</td></tr>)}{lexErrors.map((e,i)=><tr key={'e'+i} className="err-row"><td>!</td><td><span className="token-badge">ERROR</span></td><td className="mono">{e.char}</td><td>{e.column}</td><td>—</td><td className="jp-why">{e.message}</td></tr>)}</tbody></table></div></div>}
 else if(tab===2){const info=rule&&dfas[rule.pattern];const m=info?.minDfa;const run=m&&tok?runMachine(m,tok.lexeme):null;const hot=new Map();if(run)run.path.slice(1).forEach((to,i)=>{const k=`${run.path[i]}|${to}`;if(!hot.has(k))hot.set(k,[]);hot.get(k).push(i+1)});
  panel=<div className="jp-auto"><div className="jp-pick"><small>PICK A TOKEN</small>{tokens.map((t,i)=><button key={i} className={i===pickTok?'on':''} onClick={()=>setPickTok(i)}>{t.lexeme}<i>{t.type}</i></button>)}</div>
   {!tok?<div className="journey-empty">No tokens to trace.</div>:!m?<div className="journey-empty">Building the DFA for {tok.type}…</div>:<><p className="jp-info">Rule <b>{rule.name}</b> = <code>{rule.pattern}</code> compiles to {info.stats.nfaStates} NFA states → {info.stats.dfaStates} DFA → <b>{info.stats.minDfaStates} minimal</b>. Reading “{tok.lexeme}” follows {run.path.join(' → ')} and ends in an accepting state.</p><AutomataGraph states={m.states} transitions={m.transitions} highlight={new Set(run.path)} hotEdges={hot} end={run.current}/></>}</div>}
 else if(tab===3){const nts=gram?.grammar?.nonterminals||[];
  panel=<div className="jp-gram">{!gram?<div className="journey-empty">Analyzing the expression grammar…</div>:<><div className="jp-prods"><small>PRODUCTIONS · HIGHLIGHTED = USED FOR “{src}”</small>{gram.grammar.productions.map(p=><div key={p.index} className={`${used[p.text]?'used':''} ${focusNt===p.lhs?'focus':''}`} onMouseEnter={()=>setFocusNt(p.lhs)}><code>{p.text}</code>{used[p.text]?<b>×{used[p.text]}</b>:<i>unused</i>}</div>)}</div>
   <div className="jp-sets"><small>HOVER A RULE · FIRST AND FOLLOW</small>{nts.map(nt=><div key={nt} className={focusNt===nt?'focus':''} onMouseEnter={()=>setFocusNt(nt)}><b>{nt}</b><span>FIRST {`{ ${gram.first[nt].join(', ')} }`}</span><span>FOLLOW {`{ ${gram.follow[nt].join(', ')} }`}</span></div>)}<p className="jp-info">These sets fill the LL(1) table that drove the parse: {Object.values(used).reduce((a,b)=>a+b,0)} expansions for this input.</p></div></>}</div>}
 else panel=<div className="jp-tree">{tree?<><TreeDiagram tree={tree} name="overview-tree"/><Derivations d={live.accepted?live.derivations:null}/></>:<div className="journey-empty bad">No parse tree: {typeof live.error==='string'?live.error:'the input was rejected.'}</div>}</div>;
 return <div id="journey" className="journey">
  <div className="section-intro"><div><div className="eyebrow">THE COMPILER JOURNEY</div><h2>One input. Many transformations.</h2></div><p>This follows <b>your</b> expression from the pipeline above through every stage. Change it there and every view below updates.</p></div>
  <div className="journey-input"><span>INPUT</span><code>{src||'—'}</code>{live&&<em className={live.accepted?'ok':'bad'}>{live.accepted?'accepted':'rejected'}</em>}<button onClick={onOpen} disabled={!health}>Step through it in the Time machine <ArrowRight size={12}/></button></div>
  <div className="journey-steps" role="tablist">{JOURNEY.map(([id,label,sub],i)=><button key={id} role="tab" aria-selected={tab===i} className={`journey-step ${tab===i?'on':''}`} onClick={()=>setTab(i)}><div className="j-num">0{i+1}<span>{i<4&&<ArrowRight size={12}/>}</span></div><b>{label}</b><small>{sub}</small><em>{live?counts[i]:'—'}</em></button>)}</div>
  <div className="journey-panel" key={tab}>{panel}</div>
 </div>}

const BENCHES=[['lexer','Lexical analysis','Segment source into tokens with maximal munch.','lex'],['automata','Automata studio','Regex → NFA → DFA → minimal DFA.','auto'],['grammar','Grammar workbench','FIRST, FOLLOW, transforms and derivations.','gram'],['ll1','LL(1) parsing','Simulate a predictive parser step by step.','ll'],['slr','LR parsing','SLR, LALR and LR(1) side by side.','lr'],['timemachine','Time machine','Replay the whole front end, frame by frame.','tm']];
function LaunchGrid({navigate}){return <div className="launch-grid"><div className="launch-title"><div className="eyebrow">OPEN A BENCH</div><h2>Choose your instrument.</h2><p>Hover a bench for a preview of what it does, or press its number key.</p></div>{BENCHES.map(([id,label,desc,glyph],i)=>{const Icon=modules.find(m=>m.id===id)?.icon||Activity;return <button className="launch-card" key={id} onClick={()=>navigate(id)}><div className="card-index"><span>0{i+1}</span><Icon size={17}/></div><b>{label}</b><small>{desc}</small><BenchGlyph kind={glyph}/><kbd className="card-key">{i+1}</kbd><ArrowRight className="card-arrow" size={15}/></button>})}</div>}

function BenchGlyph({kind}){
 const common={className:`glyph glyph-${kind}`,viewBox:'0 0 160 40',width:160,height:40,'aria-hidden':true};
 if(kind==='lex')return <svg {...common}><rect className="g-scan" x="2" y="8" width="26" height="22" rx="2"/>{['a','=','b','+','12'].map((t,i)=><text key={i} x={[8,36,58,84,108][i]} y="24">{t}</text>)}</svg>;
 if(kind==='auto')return <svg {...common}><path className="g-edge" d="M24 20 H66 M94 20 H136"/>{[14,80,146].map((x,i)=><circle key={i} cx={x} cy="20" r="10" className={i===2?'g-acc':''}/>)}<circle className="g-dot" cx="24" cy="20" r="3"/></svg>;
 if(kind==='gram')return <svg {...common}>{['FIRST','{','(','id','}'].map((t,i)=><text key={i} className={`g-pop g-pop${i}`} x={[2,48,62,78,98][i]} y="25">{t}</text>)}</svg>;
 if(kind==='ll')return <svg {...common}>{[0,1,2,3].map(i=><rect key={i} className={`g-stack g-stack${i}`} x={6+i*30} y="12" width="26" height="16" rx="2"/>)}<text x="128" y="25">id $</text></svg>;
 if(kind==='lr')return <svg {...common}>{['I0','I3','I7'].map((t,i)=><g key={i} className={`g-state g-state${i}`}><rect x={4+i*44} y="9" width="36" height="22" rx="3"/><text x={22+i*44} y="24" textAnchor="middle">{t}</text></g>)}<text x="138" y="24">r3</text></svg>;
 return <svg {...common}><line className="g-track" x1="6" y1="20" x2="154" y2="20"/>{[0,1,2,3,4,5].map(i=><circle key={i} cx={10+i*28} cy="20" r="2.5" className="g-tick"/>)}<circle className="g-knob" cx="10" cy="20" r="6"/></svg>;
}

const KIND_LABEL={all:'All',regex:'Regex',lexer:'Lexer',grammar:'Grammar',ll1:'LL(1)',slr:'LR',timemachine:'Time machine'};
function ExampleStrip({examples,onExample}){
 const [kind,setKind]=useState('all');
 const kinds=['all',...new Set(examples.map(e=>e.kind))];
 const list=examples.filter(e=>kind==='all'||e.kind===kind);
 return <div className="example-strip"><div><div className="eyebrow">A GOOD PLACE TO START</div><h2>Experiments with a point of view.</h2><p className="strip-note">{examples.length} curated experiments. Each one loads straight into its bench with the input already filled in.</p><button className="button secondary" disabled={!examples.length} onClick={()=>onExample(examples[Math.floor(Math.random()*examples.length)])}><Sparkles size={14}/> Surprise me</button></div>
  <div className="strip-right"><div className="strip-filters">{kinds.map(k=><button key={k} className={kind===k?'on':''} onClick={()=>setKind(k)}>{KIND_LABEL[k]||k}<i>{k==='all'?examples.length:examples.filter(e=>e.kind===k).length}</i></button>)}</div>
   <div className="mini-examples">{list.map(e=><button key={e.id} onClick={()=>onExample(e)}><small>{e.kicker} · {String(e.difficulty||'').toUpperCase()}</small><b>{e.title}</b><span>{e.tagline}</span><ArrowRight size={14}/></button>)}</div></div>
 </div>}

createRoot(document.getElementById('root')).render(<App/>);
