import React,{useEffect,useId,useRef,useState}from"react";

const toastListeners=new Set();
const promptListeners=new Set();

export function notify(message,{type="error",duration=4200,title}={}){
  if(!message)return;
  const id=globalThis.crypto?.randomUUID?.()||`${Date.now()}-${Math.random()}`;
  toastListeners.forEach(listener=>listener({id,message:String(message),type,duration,title}));
}

export function promptDialog({title="Enter a value",label="Value",defaultValue="",placeholder="",confirmLabel="Save",cancelLabel="Cancel"}={}){
  return new Promise(resolve=>promptListeners.forEach(listener=>listener({title,label,defaultValue,placeholder,confirmLabel,cancelLabel,resolve})));
}

export function FeedbackHost(){
  const[toasts,setToasts]=useState([]),[prompt,setPrompt]=useState(null),[value,setValue]=useState("");
  const inputRef=useRef(null),titleId=useId(),descriptionId=useId();
  useEffect(()=>{const onToast=toast=>{setToasts(current=>[...current.slice(-3),toast]);setTimeout(()=>setToasts(current=>current.filter(item=>item.id!==toast.id)),toast.duration)};toastListeners.add(onToast);return()=>toastListeners.delete(onToast)},[]);
  useEffect(()=>{const onPrompt=options=>{setPrompt(options);setValue(options.defaultValue||"")};promptListeners.add(onPrompt);return()=>promptListeners.delete(onPrompt)},[]);
  useEffect(()=>{if(!prompt)return;const previous=document.activeElement;inputRef.current?.focus();const onKey=event=>{if(event.key==="Escape")finish(null)};document.addEventListener("keydown",onKey);return()=>{document.removeEventListener("keydown",onKey);previous?.focus?.()}},[prompt]);
  function finish(result){prompt?.resolve(result);setPrompt(null)}
  return <>
    <div className="app-toast-region" aria-live="polite" aria-relevant="additions">{toasts.map(toast=><div key={toast.id} className={`app-toast app-toast-${toast.type}`} role={toast.type==="error"?"alert":"status"}><div><b>{toast.title||({error:"Something went wrong",success:"Saved",info:"SocialN"}[toast.type])}</b><span>{toast.message}</span></div><button type="button" aria-label="Dismiss notification" onClick={()=>setToasts(current=>current.filter(item=>item.id!==toast.id))}>×</button></div>)}</div>
    {prompt&&<div className="modal-backdrop app-prompt-backdrop" role="presentation" onMouseDown={()=>finish(null)}><form className="app-prompt" role="dialog" aria-modal="true" aria-labelledby={titleId} aria-describedby={descriptionId} onMouseDown={event=>event.stopPropagation()} onSubmit={event=>{event.preventDefault();finish(value)}}><h3 id={titleId}>{prompt.title}</h3><label id={descriptionId} htmlFor={`${descriptionId}-input`}>{prompt.label}</label><input ref={inputRef} id={`${descriptionId}-input`} value={value} placeholder={prompt.placeholder} onChange={event=>setValue(event.target.value)}/><div className="app-prompt-actions"><button type="button" className="secondary" onClick={()=>finish(null)}>{prompt.cancelLabel}</button><button className="primary">{prompt.confirmLabel}</button></div></form></div>}
  </>;
}

export function LoadingSkeleton({rows=3,label="Loading content"}){
  return <div className="loading-skeleton" role="status" aria-label={label}>{Array.from({length:rows},(_,index)=><span key={index} style={{"--skeleton-width":`${92-index*11}%`}}/>)}<span className="sr-only">{label}</span></div>;
}
