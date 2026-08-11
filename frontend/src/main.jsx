import React,{Component,useEffect,useRef,useState}from"react";import{createRoot}from"react-dom/client";import{Search,Home,Users,MessageCircle,Bell,Settings,Image as ImageIcon,ThumbsUp,MessageSquare,Share2,Send,LogOut,Camera,UserPlus,UserCheck,ShieldBan,Menu,X,Check,MoreHorizontal,MoreVertical,Edit2,Trash2,Pin,Archive,Paperclip,Mic,Square,FileText,Download,Maximize2,Sun,Moon,Languages,Smile}from"lucide-react";import{LANGUAGES,setSiteLanguage}from"./i18n";import"./styles.css";
const API=import.meta.env.VITE_API_URL||"http://localhost:8000",WS=API.replace(/^http/,"ws");const tok=()=>localStorage.getItem("socialn_token"),asset=u=>u?`${API}${u}`:null;
const REACTIONS=[{key:"like",emoji:"👍",label:"Like"},{key:"love",emoji:"❤️",label:"Love"},{key:"haha",emoji:"😂",label:"Haha"},{key:"wow",emoji:"😮",label:"Wow"},{key:"sad",emoji:"😢",label:"Sad"},{key:"angry",emoji:"😡",label:"Angry"}];
const STICKERS=["😀","😂","🥰","😍","😎","🥳","🤩","🤗","🤔","😴","😭","😡","👍","👏","🙏","💪","❤️","💖","🔥","🎉","✨","🌈","🐶","🐱","🐼","🦊","🐸","🦄","🍕","🍰","☕","⚽","🎮","🚀","🌻","🎁"];
function messageStickers(value){if(!value)return[];try{const parsed=JSON.parse(value);return Array.isArray(parsed)?parsed.filter(x=>typeof x==="string").slice(0,24):[value]}catch{return[value]}}
const reactionInfo=key=>REACTIONS.find(x=>x.key===key)||REACTIONS[0];
function apiError(detail){if(Array.isArray(detail))return detail.map(x=>x?.msg||String(x)).join("; ");if(detail&&typeof detail==="object")return detail.message||JSON.stringify(detail);return detail||"Request failed"}
async function api(p,o={}){const h=new Headers(o.headers||{});if(tok())h.set("Authorization",`Bearer ${tok()}`);if(!(o.body instanceof FormData)&&o.body!==undefined)h.set("Content-Type","application/json");const r=await fetch(`${API}${p}`,{...o,headers:h}),d=await r.json().catch(()=>({}));if(!r.ok)throw Error(apiError(d.detail));return d}

class ErrorBoundary extends Component{
  constructor(props){super(props);this.state={hasError:false,error:""}}
  static getDerivedStateFromError(error){return{hasError:true,error:error?.message||"Unknown UI error"}}
  componentDidCatch(error,info){console.error("SocialN UI crash:",error,info)}
  render(){
    if(this.state.hasError){
      return <div className="ui-error">
        <h2>SocialN encountered a UI error</h2>
        <p>{this.state.error}</p>
        <button className="primary" onClick={()=>window.location.reload()}>Reload SocialN</button>
      </div>
    }
    return this.props.children
  }
}
let openConfirmDialog=null;
function confirmDialog(options){return new Promise(resolve=>openConfirmDialog?openConfirmDialog({...options,resolve}):resolve(false))}
function ConfirmHost(){
  const[dialog,setDialog]=useState(null);
  useEffect(()=>{openConfirmDialog=setDialog;return()=>{openConfirmDialog=null}},[]);
  useEffect(()=>{if(!dialog)return;const key=e=>{if(e.key==="Escape"){dialog.resolve(false);setDialog(null)}};window.addEventListener("keydown",key);return()=>window.removeEventListener("keydown",key)},[dialog]);
  if(!dialog)return null;
  function finish(value){dialog.resolve(value);setDialog(null)}
  return <div className="modal-backdrop confirm-dialog-backdrop" role="presentation" onMouseDown={()=>finish(false)}><div className="confirm-dialog" role="alertdialog" aria-modal="true" aria-labelledby="confirm-dialog-title" aria-describedby="confirm-dialog-description" onMouseDown={e=>e.stopPropagation()}>
    <div className="confirm-dialog-icon"><Trash2 size={25}/></div>
    <div className="confirm-dialog-copy"><h3 id="confirm-dialog-title">{dialog.title||"Are you sure?"}</h3><p id="confirm-dialog-description">{dialog.message}</p>{dialog.detail&&<div className="confirm-dialog-detail">{dialog.detail}</div>}</div>
    <div className="confirm-dialog-actions"><button className="secondary" autoFocus onClick={()=>finish(false)}>{dialog.cancelLabel||"Cancel"}</button><button className="danger confirm-danger" onClick={()=>finish(true)}>{dialog.confirmLabel||"Delete"}</button></div>
  </div></div>
}
function Avatar({user,size=42,onClick}){return user?.avatar_url?<img className="avatar clickable" style={{width:size,height:size}} src={asset(user.avatar_url)} onClick={onClick}/>:<div className="avatar avatar-fallback clickable" style={{width:size,height:size}} onClick={onClick}>{(user?.name||"?")[0]}</div>}
function LanguagePicker({value,onChange,compact=false}){return <div className={`language-picker ${compact?"compact":""}`}><Languages size={18}/><select value={value} onChange={e=>onChange(e.target.value)} aria-label="Language">{LANGUAGES.map(language=><option key={language.code} value={language.code}>{language.label}</option>)}</select></div>}
function Login({onLogin,language,onLanguageChange}){const[mode,setMode]=useState("login"),[f,setF]=useState({email:"",username:"",name:"",password:""}),[err,setErr]=useState("");async function sub(e){e.preventDefault();try{const d=await api(`/api/auth/${mode}`,{method:"POST",body:JSON.stringify(f)});localStorage.setItem("socialn_token",d.access_token);onLogin(d.user)}catch(e){setErr(e.message)}}return <div className="auth-shell"><div className="auth-stack"><div className="auth-card"><div className="brand big">Social<span>N</span></div><form onSubmit={sub}>{mode==="register"&&<><input placeholder="Full name" onChange={e=>setF({...f,name:e.target.value})}/><input placeholder="Username" onChange={e=>setF({...f,username:e.target.value})}/></>}<input type="email" placeholder="Email" onChange={e=>setF({...f,email:e.target.value})}/><input type="password" placeholder="Password" onChange={e=>setF({...f,password:e.target.value})}/>{err&&<div className="error">{err}</div>}<button className="primary wide">{mode==="login"?"Log in":"Register"}</button></form><button className="link-btn" onClick={()=>setMode(mode==="login"?"register":"login")}>{mode==="login"?"Create account":"Back to login"}</button></div><LanguagePicker compact value={language} onChange={onLanguageChange}/></div></div>}

function PostComposer({onCreated}){
  const[content,setContent]=useState("");
  const[privacy,setPrivacy]=useState("public");
  const[file,setFile]=useState(null);
  const[sticker,setSticker]=useState(null),[showStickers,setShowStickers]=useState(false);
  const[busy,setBusy]=useState(false);
  const[error,setError]=useState("");

  async function submit(e){
    e.preventDefault();
    if(!content.trim()&&!file&&!sticker)return;
    setBusy(true);setError("");
    try{
      let image_url=null;
      if(file){
        const body=new FormData();body.append("file",file);
        image_url=(await api("/api/upload",{method:"POST",body})).url;
      }
      const post=await api("/api/posts",{method:"POST",body:JSON.stringify({content,privacy,image_url,sticker})});
      setContent("");setFile(null);setSticker(null);setShowStickers(false);onCreated?.(post);
    }catch(e){setError(e.message)}finally{setBusy(false)}
  }

  return <form className="card composer" onSubmit={submit}>
    <div className="composer-title">Create post</div>
    <div className="composer-row"><textarea value={content} onChange={e=>setContent(e.target.value)} placeholder="What's on your mind?"/></div>
    {file&&<div className="file-chip">{file.name}</div>}
    {sticker&&<div className="selected-sticker"><span>{sticker}</span><button type="button" onClick={()=>setSticker(null)} aria-label="Remove sticker"><X size={17}/></button></div>}
    {error&&<div className="error">{error}</div>}
    <div className="composer-actions">
      <label className="action"><ImageIcon size={18}/> Photo<input hidden type="file" accept="image/*" onChange={e=>setFile(e.target.files?.[0]||null)}/></label>
      <div className="sticker-control"><button type="button" className={`action sticker-trigger ${showStickers?"active":""}`} onClick={()=>setShowStickers(!showStickers)}><Smile size={19}/> Stickers</button>{showStickers&&<div className="sticker-library"><div className="sticker-library-head"><div><b>Stickers</b><small>Choose one for your post</small></div><button type="button" className="icon-btn" onClick={()=>setShowStickers(false)}><X size={18}/></button></div><div className="sticker-grid">{STICKERS.map((item,index)=><button type="button" key={`${item}-${index}`} className={sticker===item?"selected":""} onClick={()=>{setSticker(item);setShowStickers(false)}}>{item}</button>)}</div></div>}</div>
      <select value={privacy} onChange={e=>setPrivacy(e.target.value)}><option value="public">Public</option><option value="friends">Friends</option><option value="only_me">Only me</option></select>
      <button className="primary" disabled={busy||(!content.trim()&&!file&&!sticker)}>{busy?"Posting...":"Post"}</button>
    </div>
  </form>
}

function PostCard({post,me,onOpenProfile,onUpdated,onDeleted}){
  const[comment,setComment]=useState("");
  const[editing,setEditing]=useState(false);
  const[menu,setMenu]=useState(false);
  const[draft,setDraft]=useState({content:post.content||"",privacy:post.privacy||"public",image_url:post.image_url||null,sticker:post.sticker||null});
  const[busy,setBusy]=useState(false);

  async function react(type){try{const d=await api(`/api/posts/${post.id}/like`,{method:"POST",body:JSON.stringify({reaction:type})});onUpdated?.({...post,...d})}catch(e){alert(e.message)}}
  async function addComment(e){e.preventDefault();if(!comment.trim())return;try{const row=await api(`/api/posts/${post.id}/comments`,{method:"POST",body:JSON.stringify({content:comment})});setComment("");onUpdated?.({...post,comments:[...(post.comments||[]),row]})}catch(e){alert(e.message)}}
  async function saveEdit(){setBusy(true);try{const row=await api(`/api/posts/${post.id}`,{method:"PUT",body:JSON.stringify(draft)});setEditing(false);setMenu(false);onUpdated?.(row)}catch(e){alert(e.message)}finally{setBusy(false)}}
  async function remove(){if(!await confirmDialog({title:"Delete post?",message:"This post and its activity will be permanently removed.",detail:"This action cannot be undone.",confirmLabel:"Delete post"}))return;try{await api(`/api/posts/${post.id}`,{method:"DELETE"});onDeleted?.(post.id)}catch(e){alert(e.message)}}
  async function share(){try{await api(`/api/posts/${post.id}/share`,{method:"POST"});alert("Post shared") }catch(e){alert(e.message)}}
  async function openPostAlbum(){await onOpenProfile?.(post.author.id);setTimeout(()=>document.getElementById(`profile-albums-${post.author.id}`)?.scrollIntoView({behavior:"smooth",block:"start"}),80)}
  const privacyLabel={public:"Public",friends:"Friends",only_me:"Only me"}[post.privacy]||post.privacy;

  return <article className="card post">
    <div className="post-head"><Avatar user={post.author} onClick={()=>onOpenProfile?.(post.author.id)}/><div className="post-author"><button className="name-link" onClick={()=>onOpenProfile?.(post.author.id)}><b>{post.author.name}</b></button><div className="privacy-line">{privacyLabel} · {new Date(post.created_at).toLocaleString()}</div></div>
      {post.is_owner&&<div className="post-menu-wrap"><button className="icon-btn" onClick={()=>setMenu(!menu)}><MoreHorizontal size={20}/></button>{menu&&<div className="post-menu"><button onClick={()=>{setEditing(true);setMenu(false)}}><Edit2 size={16}/> Edit</button><button className="danger-link" onClick={remove}><Trash2 size={16}/> Delete</button></div>}</div>}
    </div>
    {editing?<div className="post-edit"><textarea value={draft.content} onChange={e=>setDraft({...draft,content:e.target.value})}/><select value={draft.privacy} onChange={e=>setDraft({...draft,privacy:e.target.value})}><option value="public">Public</option><option value="friends">Friends</option><option value="only_me">Only me</option></select><div className="edit-actions"><button className="secondary" onClick={()=>setEditing(false)}>Cancel</button><button className="primary" disabled={busy} onClick={saveEdit}>Save</button></div></div>:<>{post.content&&<div className="post-content">{post.content}</div>}{post.sticker&&<div className="post-sticker" role="img" aria-label="Sticker">{post.sticker}</div>}{post.album&&<button className="post-album-link" onClick={openPostAlbum}><ImageIcon size={15}/> {post.album.name}</button>}{post.image_url&&(post.media_type==="video"?<video className="post-image post-video" src={asset(post.image_url)} controls preload="metadata" playsInline/>:<img className="post-image" src={asset(post.image_url)} alt="Post"/>)}</>}
    {post.shared_post&&<div className="shared-card"><div className="shared-author"><Avatar user={post.shared_post.author} size={34}/><b>{post.shared_post.author.name}</b></div>{post.shared_post.content&&<div className="shared-content">{post.shared_post.content}</div>}{post.shared_post.sticker&&<div className="post-sticker shared-sticker" role="img" aria-label="Sticker">{post.shared_post.sticker}</div>}{post.shared_post.image_url&&(post.shared_post.media_type==="video"?<video className="shared-image" src={asset(post.shared_post.image_url)} controls preload="metadata"/>:<img className="shared-image" src={asset(post.shared_post.image_url)} alt="Shared post"/>)}</div>}
    <div className="post-stats"><span className="reaction-summary">{Object.entries(post.reaction_counts||{}).filter(([,n])=>n>0).map(([key])=><span key={key}>{reactionInfo(key).emoji}</span>)} {post.likes_count||0} reactions</span><span>{post.comments?.length||0} comments</span></div>
    <div className="post-buttons"><div className="reaction-wrap"><button className={post.my_reaction?"active":""} onClick={()=>react(post.my_reaction||"like")}><span>{post.my_reaction?reactionInfo(post.my_reaction).emoji:<ThumbsUp size={18}/>}</span> {post.my_reaction?reactionInfo(post.my_reaction).label:"Like"}</button><div className="reaction-picker">{REACTIONS.map(r=><button key={r.key} title={r.label} onClick={()=>react(r.key)}>{r.emoji}</button>)}</div></div><button onClick={()=>document.getElementById(`comment-${post.id}`)?.focus()}><MessageSquare size={18}/> Comment</button><button onClick={share}><Share2 size={18}/> Share</button></div>
    <div>{(post.comments||[]).map(c=><div className="comment" key={c.id}><Avatar user={c.author} size={32}/><div className="comment-body"><b>{c.author.name}</b><div>{c.content}</div></div></div>)}</div>
    <form className="comment-box" onSubmit={addComment}><input id={`comment-${post.id}`} value={comment} onChange={e=>setComment(e.target.value)} placeholder="Write a comment..."/><button><Send size={16}/></button></form>
  </article>
}

function ImageEditor({file,mode,onCancel,onSave}){
  const canvasRef=useRef(null),imageRef=useRef(null),dragRef=useRef(null);
  const[zoom,setZoom]=useState(1),[pan,setPan]=useState({x:0,y:0}),[ready,setReady]=useState(false),[saving,setSaving]=useState(false);
  const isAvatar=mode==="avatar",width=isAvatar?512:1200,height=isAvatar?512:450;

  useEffect(()=>{
    const url=URL.createObjectURL(file),img=new Image();
    img.onload=()=>{imageRef.current=img;setReady(true)};img.src=url;
    return()=>URL.revokeObjectURL(url);
  },[file]);

  function geometry(){
    const img=imageRef.current;if(!img)return null;
    const scale=Math.max(width/img.width,height/img.height)*zoom,dw=img.width*scale,dh=img.height*scale;
    const rawX=(width-dw)/2+pan.x,rawY=(height-dh)/2+pan.y;
    return{dw,dh,x:Math.min(0,Math.max(width-dw,rawX)),y:Math.min(0,Math.max(height-dh,rawY))};
  }
  useEffect(()=>{
    const canvas=canvasRef.current,img=imageRef.current,g=geometry();if(!canvas||!img||!g)return;
    const ctx=canvas.getContext("2d");ctx.clearRect(0,0,width,height);ctx.drawImage(img,g.x,g.y,g.dw,g.dh);
  },[ready,zoom,pan.x,pan.y]);
  function pointerDown(e){e.currentTarget.setPointerCapture(e.pointerId);dragRef.current={x:e.clientX,y:e.clientY,pan}}
  function pointerMove(e){if(!dragRef.current)return;const rect=e.currentTarget.getBoundingClientRect(),factor=width/rect.width;setPan({x:dragRef.current.pan.x+(e.clientX-dragRef.current.x)*factor,y:dragRef.current.pan.y+(e.clientY-dragRef.current.y)*factor})}
  function pointerUp(){dragRef.current=null}
  async function confirm(){
    setSaving(true);
    try{const blob=await new Promise((resolve,reject)=>canvasRef.current.toBlob(b=>b?resolve(b):reject(Error("Cannot process image")),"image/jpeg",.9));await onSave(new File([blob],`${mode}-${Date.now()}.jpg`,{type:"image/jpeg"}))}finally{setSaving(false)}
  }
  return <div className="modal-backdrop image-editor-backdrop"><div className="image-editor-modal">
    <div className="image-editor-head"><div><h3>{isAvatar?"Edit profile picture":"Edit cover photo"}</h3><p>{isAvatar?"Drag to choose the square area. It will appear circular on your profile.":"Drag the photo up or down to choose the visible cover area."}</p></div><button className="icon-btn" onClick={onCancel}><X/></button></div>
    <div className={`image-editor-stage ${isAvatar?"avatar-stage":"cover-stage"}`}><canvas ref={canvasRef} width={width} height={height} onPointerDown={pointerDown} onPointerMove={pointerMove} onPointerUp={pointerUp} onPointerCancel={pointerUp}/>{isAvatar&&<div className="avatar-crop-mask"/>}</div>
    <label className="zoom-control"><span>Zoom</span><input type="range" min="1" max="3" step="0.01" value={zoom} onChange={e=>setZoom(Number(e.target.value))}/></label>
    <div className="modal-actions"><button className="secondary" onClick={onCancel}>Cancel</button><button className="primary" disabled={!ready||saving} onClick={confirm}>{saving?"Processing...":"Save photo"}</button></div>
  </div></div>
}

function ProfileAlbums({user,me,onProfileChanged}){
  const[albums,setAlbums]=useState([]),[selected,setSelected]=useState(null),[creating,setCreating]=useState(false),[editing,setEditing]=useState(false),[busy,setBusy]=useState(false),[preview,setPreview]=useState(null);
  const[selecting,setSelecting]=useState(false),[selectedMedia,setSelectedMedia]=useState(new Set());
  const[form,setForm]=useState({name:"",description:"",privacy:"friends"});
  const[editForm,setEditForm]=useState({name:"",description:"",privacy:"friends"});
  const mine=Number(user.id)===Number(me.id);
  async function load(){try{setAlbums(await api(`/api/albums/user/${user.id}`))}catch(e){console.error(e);setAlbums([])}}
  useEffect(()=>{load();setSelected(null)},[user.id,user.avatar_url,user.cover_url]);
  async function openAlbum(id){try{setSelecting(false);setSelectedMedia(new Set());setSelected(await api(`/api/albums/${id}`))}catch(e){alert(e.message)}}
  async function create(e){e.preventDefault();setBusy(true);try{const row=await api("/api/albums",{method:"POST",body:JSON.stringify(form)});setCreating(false);setForm({name:"",description:"",privacy:"friends"});await load();await openAlbum(row.id)}catch(e){alert(e.message)}finally{setBusy(false)}}
  function beginEdit(){setEditForm({name:selected.name,description:selected.description||"",privacy:selected.privacy});setEditing(true)}
  async function saveAlbum(e){e.preventDefault();setBusy(true);try{await api(`/api/albums/${selected.id}`,{method:"PUT",body:JSON.stringify(editForm)});setEditing(false);await load();await openAlbum(selected.id);await onProfileChanged?.()}catch(e){alert(e.message)}finally{setBusy(false)}}
  async function deleteAlbum(){if(!await confirmDialog({title:"Delete album?",message:`“${selected.name}” will be permanently deleted.`,detail:"All photos, videos and linked timeline posts in this album will also be removed.",confirmLabel:"Delete album"}))return;setBusy(true);try{await api(`/api/albums/${selected.id}`,{method:"DELETE"});setEditing(false);setSelected(null);setPreview(null);await load();await onProfileChanged?.()}catch(e){alert(e.message)}finally{setBusy(false)}}
  async function upload(files){
    if(!selected||!files?.length)return;setBusy(true);
    try{for(const file of files){const fd=new FormData();fd.append("file",file);fd.append("caption","");await api(`/api/albums/${selected.id}/media`,{method:"POST",body:fd})}await openAlbum(selected.id);await load();await onProfileChanged?.()}catch(e){alert(e.message)}finally{setBusy(false)}
  }
  function toggleMedia(id){setSelectedMedia(prev=>{const next=new Set(prev);next.has(id)?next.delete(id):next.add(id);return next})}
  async function deleteSelected(){
    if(!selectedMedia.size||!await confirmDialog({title:`Delete ${selectedMedia.size} selected item${selectedMedia.size===1?"":"s"}?`,message:"The selected media will be permanently removed from this album.",detail:"Linked timeline posts will also be removed.",confirmLabel:"Delete selected"}))return;
    setBusy(true);
    try{for(const id of selectedMedia)await api(`/api/albums/${selected.id}/media/${id}`,{method:"DELETE"});setSelecting(false);setSelectedMedia(new Set());await openAlbum(selected.id);await load();await onProfileChanged?.()}catch(e){alert(e.message)}finally{setBusy(false)}
  }
  return <section id={`profile-albums-${user.id}`} className="card profile-albums-section"><div className="albums-head"><div><h2>Albums</h2><p className="muted">Profile pictures, cover photos and timeline media</p></div>{mine&&<button className="primary" onClick={()=>setCreating(true)}>Create album</button>}</div>
    <div className="album-grid">{albums.map(a=><button className="album-card" key={a.id} onClick={()=>openAlbum(a.id)}><div className="album-cover">{a.cover?(a.cover_type==="video"?<video src={asset(a.cover)} muted preload="metadata"/>:<img src={asset(a.cover)} alt={a.name}/>):<ImageIcon size={38}/>}</div><b>{a.name}</b>{a.description&&<small>{a.description}</small>}<span>{a.media_count} item{a.media_count===1?"":"s"} · {a.privacy}</span></button>)}</div>
    {creating&&<div className="modal-backdrop" onClick={()=>setCreating(false)}><form className="album-create-modal" onSubmit={create} onClick={e=>e.stopPropagation()}><div className="album-modal-title"><h3>Create album</h3><button type="button" className="icon-btn" onClick={()=>setCreating(false)}><X/></button></div><label>Album name<input required maxLength="150" value={form.name} onChange={e=>setForm({...form,name:e.target.value})}/></label><label>Description / notes<textarea maxLength="2000" placeholder="Write something about this album..." value={form.description} onChange={e=>setForm({...form,description:e.target.value})}/></label><label>Privacy<select value={form.privacy} onChange={e=>setForm({...form,privacy:e.target.value})}><option value="friends">Friends</option><option value="public">Public</option><option value="only_me">Only me</option></select></label><button className="primary" disabled={busy}>{busy?"Creating...":"Create album"}</button></form></div>}
    {selected&&<div className="modal-backdrop album-view-backdrop" onClick={()=>setSelected(null)}><div className="album-view-modal" onClick={e=>e.stopPropagation()}><div className="album-modal-title"><div><h3>{selected.name}</h3><p>{selected.description||"No description"}</p><small>{selected.media_count} items · {selected.privacy}</small></div><button className="icon-btn" onClick={()=>setSelected(null)}><X/></button></div><div className="album-toolbar">{selected.is_owner&&selected.kind==="custom"&&<><label className="primary album-upload-button"><ImageIcon size={17}/>{busy?"Uploading...":"Add photos/videos"}<input hidden multiple type="file" accept="image/*,video/*" disabled={busy} onChange={e=>{upload([...e.target.files]);e.target.value=""}}/></label><button className="secondary" disabled={busy} onClick={beginEdit}><Edit2 size={16}/> Edit album</button><button className="danger" disabled={busy} onClick={deleteAlbum}><Trash2 size={16}/> Delete album</button></>}{selected.is_owner&&selected.media.length>0&&<button className={selecting?"secondary active-select":"secondary"} onClick={()=>{setSelecting(!selecting);setSelectedMedia(new Set())}}>{selecting?"Cancel selection":"Select media"}</button>}{selecting&&selectedMedia.size>0&&<button className="danger" disabled={busy} onClick={deleteSelected}><Trash2 size={16}/> Delete ({selectedMedia.size})</button>}</div><div className="album-media-grid">{selected.media.length===0?<div className="empty">No photos or videos yet.</div>:selected.media.map(m=><button className={selectedMedia.has(m.id)?"selected":""} key={m.id} onClick={()=>selecting?toggleMedia(m.id):setPreview({type:m.type,url:asset(m.url),name:m.caption||selected.name})}>{m.type==="video"?<video src={asset(m.url)} muted preload="metadata"/>:<img src={asset(m.url)} alt={m.caption||selected.name}/>}<span>{selecting?(selectedMedia.has(m.id)?"✓":"○"):(m.type==="video"?"▶":"")}</span></button>)}</div></div></div>}
    {editing&&selected&&<div className="modal-backdrop album-edit-backdrop" onClick={()=>setEditing(false)}><form className="album-create-modal" onSubmit={saveAlbum} onClick={e=>e.stopPropagation()}><div className="album-modal-title"><h3>Edit album</h3><button type="button" className="icon-btn" onClick={()=>setEditing(false)}><X/></button></div><label>Album name<input required maxLength="150" value={editForm.name} onChange={e=>setEditForm({...editForm,name:e.target.value})}/></label><label>Description / notes<textarea maxLength="2000" placeholder="Write something about this album..." value={editForm.description} onChange={e=>setEditForm({...editForm,description:e.target.value})}/></label><label>Privacy<select value={editForm.privacy} onChange={e=>setEditForm({...editForm,privacy:e.target.value})}><option value="friends">Friends</option><option value="public">Public</option><option value="only_me">Only me</option></select></label><button className="primary" disabled={busy}>{busy?"Saving...":"Save changes"}</button></form></div>}
    {preview&&<MediaPreview media={preview} onClose={()=>setPreview(null)}/>} 
  </section>
}

function Profile({data,me,reload,message,open}){
  const user=data.user;
  const mine=user.id===me.id;
  const [editing,setEditing]=useState(false);
  const [form,setForm]=useState({
    name:user.name||"",
    dob:user.dob||"",
    hometown:user.hometown||"",
    gender:user.gender||"",
    relationship_status:user.relationship_status||"",
    bio:user.bio||""
  });
  const [coverBusy,setCoverBusy]=useState(false);
  const [confirmUnfriend,setConfirmUnfriend]=useState(false);
  const [imageEditor,setImageEditor]=useState(null);
  const [photoMenu,setPhotoMenu]=useState(null);
  const [contentVersion,setContentVersion]=useState(0);

  useEffect(()=>{
    setForm({
      name:user.name||"",
      dob:user.dob||"",
      hometown:user.hometown||"",
      gender:user.gender||"",
      relationship_status:user.relationship_status||"",
      bio:user.bio||""
    });
  },[user.id,user.name,user.dob,user.hometown,user.gender,user.relationship_status,user.bio]);

  async function save(){
    try{
      await api("/api/users/me",{
        method:"PUT",
        body:JSON.stringify({...form,dob:form.dob||null})
      });
      setEditing(false);
      await reload(user.id);
    }catch(e){alert(e.message)}
  }

  async function upload(kind,file){
    if(!file)return;
    if(kind==="cover")setCoverBusy(true);
    try{
      const fd=new FormData();
      fd.append("file",file);
      await api(`/api/users/me/${kind}`,{method:"POST",body:fd});
      await reload(user.id);
    }catch(e){alert(e.message)}
    finally{setCoverBusy(false)}
  }

  async function saveEditedImage(file){
    const kind=imageEditor.kind;setImageEditor(null);await upload(kind,file);
  }
  async function deletePhoto(){
    const kind=photoMenu;if(!kind)return;
    if(!await confirmDialog({title:`Remove ${kind==="avatar"?"profile picture":"cover photo"}?`,message:`Your current ${kind==="avatar"?"profile picture":"cover photo"} will be removed from your profile.`,detail:"The linked timeline post and album item will also be removed.",confirmLabel:"Remove photo"}))return;
    try{await api(`/api/users/me/${kind}`,{method:"DELETE"});setPhotoMenu(null);await reload(user.id)}catch(e){alert(e.message)}
  }

  async function friendshipAction(){
    try{
      if(data.relationship==="none"){
        await api(`/api/friends/${user.id}`,{method:"POST"});
      }else if(data.relationship==="incoming_request"){
        await api(`/api/friends/${data.incoming_request_id}/accept`,{method:"POST"});
      }else if(data.relationship==="friends"){
        setConfirmUnfriend(true);
        return;
      }
      await reload(user.id);
    }catch(e){alert(e.message)}
  }

  async function confirmRemoveFriend(){
    try{
      await api(`/api/friends/${user.id}`,{method:"DELETE"});
      setConfirmUnfriend(false);
      await reload(user.id);
    }catch(e){alert(e.message)}
  }

  async function block(){
    try{
      await api(`/api/users/${user.id}/block`,{method:"POST"});
      alert("User blocked");
    }catch(e){alert(e.message)}
  }

  return <>
    <div className="profile">
      <div className={`cover ${mine&&user.cover_url?"photo-clickable":""}`} style={user.cover_url?{backgroundImage:`url(${asset(user.cover_url)})`}:{}} onClick={()=>mine&&user.cover_url&&setPhotoMenu("cover")}>
        {mine&&<label className="cover-edit" onClick={e=>e.stopPropagation()}><Camera size={17}/>{coverBusy?"Uploading...":"Change cover photo"}<input hidden type="file" accept="image/*" onChange={e=>{const file=e.target.files?.[0];if(file)setImageEditor({kind:"cover",file});e.target.value=""}}/></label>}
      </div>

      <div className="profile-body">
        <div className="profile-top">
          <div className="profile-avatar-wrap">
            <Avatar user={user} size={112} onClick={()=>mine&&user.avatar_url&&setPhotoMenu("avatar")}/>
            {mine&&<label className="avatar-edit"><Camera size={15}/><input hidden type="file" accept="image/*" onChange={e=>{const file=e.target.files?.[0];if(file)setImageEditor({kind:"avatar",file});e.target.value=""}}/></label>}
          </div>

          <div className="profile-title">
            <h1>{user.name}</h1>
            <p className="muted">@{user.username}</p>
            {!mine&&<p className="muted">{data.mutual_friends_count||0} mutual friends</p>}
          </div>

          <div className="profile-actions">
            {mine
              ? <button className="secondary" onClick={()=>setEditing(!editing)}><Edit2 size={17}/> Edit profile</button>
              : <>
                  <button className="primary" disabled={data.relationship==="outgoing_request"} onClick={friendshipAction}>
                    {data.relationship==="friends"
                      ? <><UserCheck size={17}/> Friends</>
                      : data.relationship==="incoming_request"
                        ? <><Check size={17}/> Confirm request</>
                        : data.relationship==="outgoing_request"
                          ? "Request sent"
                          : <><UserPlus size={17}/> Add friend</>}
                  </button>
                  <button className="secondary" onClick={()=>message(user)}><MessageCircle size={17}/> Message</button>
                  <button className="danger" onClick={block}><ShieldBan size={17}/> Block</button>
                </>
            }
          </div>
        </div>

        {editing?<div className="edit-profile-card">
          <h3>Edit profile</h3>

          <div className="edit-grid profile-edit-grid">
            <label>
              <span>Full name</span>
              <input value={form.name} onChange={e=>setForm({...form,name:e.target.value})}/>
            </label>

            <label>
              <span>Date of birth</span>
              <input type="date" value={form.dob} onChange={e=>setForm({...form,dob:e.target.value})}/>
            </label>

            <label>
              <span>Hometown</span>
              <input placeholder="Hometown" value={form.hometown} onChange={e=>setForm({...form,hometown:e.target.value})}/>
            </label>

            <label>
              <span>Gender</span>
              <select value={form.gender} onChange={e=>setForm({...form,gender:e.target.value})}>
                <option value="">Not specified</option>
                <option value="male">Male</option>
                <option value="female">Female</option>
                <option value="other">Other</option>
                <option value="prefer_not_to_say">Prefer not to say</option>
              </select>
            </label>

            <label>
              <span>Relationship status</span>
              <select value={form.relationship_status} onChange={e=>setForm({...form,relationship_status:e.target.value})}>
                <option value="">Not specified</option>
                <option value="single">Single</option>
                <option value="in_a_relationship">In a relationship</option>
                <option value="engaged">Engaged</option>
                <option value="married">Married</option>
                <option value="complicated">It's complicated</option>
                <option value="prefer_not_to_say">Prefer not to say</option>
              </select>
            </label>

            <label className="full-row">
              <span>Bio</span>
              <textarea placeholder="Bio" value={form.bio} onChange={e=>setForm({...form,bio:e.target.value})}/>
            </label>

            <div className="edit-actions full-row">
              <button className="secondary" onClick={()=>setEditing(false)}>Cancel</button>
              <button className="primary" onClick={save}>Save changes</button>
            </div>
          </div>
        </div>:<div className="profile-info profile-info-grid">
          {user.bio&&<p className="profile-bio">{user.bio}</p>}
          <span>📍 {user.hometown||"Hometown not set"}</span>
          <span>🎂 {user.dob?new Date(user.dob).toLocaleDateString():"Birthday not set"}</span>
          <span>⚧ {formatGender(user.gender)}</span>
          <span>❤️ {formatRelationship(user.relationship_status)}</span>
        </div>}

        {!mine&&data.mutual_friends?.length>0&&<div className="mutual-section">
          <h3>Mutual friends</h3>
          <div className="people-grid compact-grid">
            {data.mutual_friends.map(x=><button className="person person-button" key={x.id} onClick={()=>open(x.id)}><Avatar user={x} size={54}/><b>{x.name}</b><span className="muted">@{x.username}</span></button>)}
          </div>
        </div>}
      </div>
    </div>

    <ProfileAlbums user={user} me={me} onProfileChanged={async()=>{setContentVersion(v=>v+1);await reload(user.id)}}/>
    <ProfilePosts userId={user.id} me={me} open={open} refreshKey={`${user.avatar_url||""}-${user.cover_url||""}-${contentVersion}`}/>

    {imageEditor&&<ImageEditor mode={imageEditor.kind} file={imageEditor.file} onCancel={()=>setImageEditor(null)} onSave={saveEditedImage}/>} 

    {photoMenu&&<div className="modal-backdrop" onClick={()=>setPhotoMenu(null)}><div className="photo-action-modal" onClick={e=>e.stopPropagation()}>
      <img src={asset(photoMenu==="avatar"?user.avatar_url:user.cover_url)} className={photoMenu==="avatar"?"photo-action-avatar":"photo-action-cover"} alt={photoMenu==="avatar"?"Profile picture":"Cover photo"}/>
      <h3>{photoMenu==="avatar"?"Profile picture":"Cover photo"}</h3>
      <a className="secondary photo-view-link" href={asset(photoMenu==="avatar"?user.avatar_url:user.cover_url)} target="_blank" rel="noreferrer">View full photo</a>
      <label className="secondary photo-change-link"><Camera size={17}/> Change photo<input hidden type="file" accept="image/*" onChange={e=>{const file=e.target.files?.[0],kind=photoMenu;if(file){setPhotoMenu(null);setImageEditor({kind,file})}e.target.value=""}}/></label>
      <button className="danger photo-delete-button" onClick={deletePhoto}><Trash2 size={17}/> Remove photo</button>
      <button className="secondary" onClick={()=>setPhotoMenu(null)}>Cancel</button>
    </div></div>}

    {confirmUnfriend&&<div className="modal-backdrop" onClick={()=>setConfirmUnfriend(false)}>
      <div className="confirm-modal" onClick={e=>e.stopPropagation()}>
        <h3>Unfriend {user.name}?</h3>
        <p>You and {user.name} will no longer be friends. Posts shared with Friends may no longer be visible to each other.</p>
        <div className="modal-actions">
          <button className="secondary" onClick={()=>setConfirmUnfriend(false)}>Cancel</button>
          <button className="danger confirm-danger" onClick={confirmRemoveFriend}>Unfriend</button>
        </div>
      </div>
    </div>}
  </>
}

function formatGender(value){
  const map={
    male:"Male",
    female:"Female",
    other:"Other",
    prefer_not_to_say:"Prefer not to say"
  };
  return map[value]||"Gender not set";
}

function formatRelationship(value){
  const map={
    single:"Single",
    in_a_relationship:"In a relationship",
    engaged:"Engaged",
    married:"Married",
    complicated:"It's complicated",
    prefer_not_to_say:"Prefer not to say"
  };
  return map[value]||"Relationship status not set";
}

function ProfilePosts({userId,me,open,refreshKey}){
  const[posts,setPosts]=useState([]);

  async function load(){
    try{
      const rows=await api(`/api/posts/user/${userId}`);
      setPosts(Array.isArray(rows)?rows:[]);
    }catch(e){console.error(e);setPosts([])}
  }

  useEffect(()=>{load()},[userId,refreshKey]);

  if(posts.length===0)return <div className="card empty profile-posts-empty">No visible posts.</div>;

  return <div className="profile-posts">
    {posts.map(p=><PostCard key={p.id} post={p} me={me} onOpenProfile={open} onUpdated={updated=>setPosts(v=>v.map(x=>x.id===updated.id?updated:x))} onDeleted={id=>setPosts(v=>v.filter(x=>x.id!==id))}/>)}
  </div>
}

function ConversationRow({conversation,active,onOpen,onChanged,onDeleted,personalStorage=false}){
  const[menu,setMenu]=useState(false);
  async function action(kind){
    setMenu(false);
    try{
      if(kind==="delete"){
        if(!await confirmDialog({title:"Delete conversation?",message:"This conversation will be removed from your inbox.",detail:"New messages from this person can make the conversation appear again.",confirmLabel:"Delete chat"}))return;
        await api(`/api/chat/conversations/${conversation.id}`,{method:"DELETE"});
        onDeleted?.(conversation);
      }else await api(`/api/chat/conversations/${conversation.id}/${kind}`,{method:"POST"});
      onChanged?.();
    }catch(e){alert(e.message)}
  }
  return <div className={`conversation-row ${active?"active":""} ${conversation.archived?"archived":""} ${personalStorage?"self-vault":""}`}>
    <button className="conversation-main" onClick={onOpen}><Avatar user={conversation.user}/><span>{conversation.user.name}{personalStorage?" (You)":""}{conversation.pinned&&!personalStorage&&<small className="pinned-label"><Pin size={11}/> Pinned</small>}<small>{conversation.last_message||({image:"Photo",video:"Video",voice:"Voice message",file:"File",sticker:"Sticker"}[conversation.last_message_type])||(personalStorage?"Personal storage":`@${conversation.user.username}`)}</small></span></button>
    <div className="conversation-menu-wrap"><button className="conversation-more" onClick={()=>setMenu(!menu)} aria-label="Conversation actions"><MoreVertical size={18}/></button>{menu&&<div className="conversation-menu">
      {!personalStorage&&<button onClick={()=>action("pin")}><Pin size={15}/>{conversation.pinned?"Unpin":"Pin"}</button>}
      {!personalStorage&&<button onClick={()=>action("archive")}><Archive size={15}/>{conversation.archived?"Unarchive":"Archive"}</button>}
      <button className="danger-link" onClick={()=>action("delete")}><Trash2 size={15}/>Delete chat</button>
    </div>}</div>
  </div>
}

function MediaPreview({media,onClose}){
  useEffect(()=>{const close=e=>{if(e.key==="Escape")onClose()};window.addEventListener("keydown",close);return()=>window.removeEventListener("keydown",close)},[onClose]);
  if(!media)return null;
  return <div className="media-preview-backdrop" onClick={onClose}><div className="media-preview-modal" onClick={e=>e.stopPropagation()}>
    <div className="media-preview-head"><span>{media.name||"Media preview"}</span><a href={media.url} download={media.name} title="Download"><Download size={19}/></a><button onClick={onClose} aria-label="Close preview"><X size={22}/></button></div>
    <div className="media-preview-body">{media.type==="video"?<video src={media.url} controls autoPlay playsInline/>:<img src={media.url} alt={media.name||"Image preview"}/>}</div>
  </div></div>
}

function Chat({me,target,open,onChanged}){
  const [messages,setMessages]=useState([]);
  const [text,setText]=useState("");
  const [connected,setConnected]=useState(false);
  const [sending,setSending]=useState(false);
  const endRef=useRef(null);
  const wsRef=useRef(null);
  const retryRef=useRef(null);
  const pingRef=useRef(null);
  const recorderRef=useRef(null);
  const chunksRef=useRef([]);
  const typingStopRef=useRef(null);
  const typingHideRef=useRef(null);
  const[recording,setRecording]=useState(false);
  const[presence,setPresence]=useState({online:false,last_seen_at:null});
  const[isOtherTyping,setIsOtherTyping]=useState(false);
  const[previewMedia,setPreviewMedia]=useState(null);
  const[selectedStickers,setSelectedStickers]=useState([]),[showStickers,setShowStickers]=useState(false);

  function lastActiveLabel(value){
    if(!value)return "Offline";
    const seconds=Math.max(0,Math.floor((Date.now()-new Date(value.endsWith?.("Z")?value:`${value}Z`).getTime())/1000));
    if(seconds<60)return "Offline · Active just now";
    if(seconds<3600)return `Offline · Active ${Math.floor(seconds/60)} minute${seconds<120?"":"s"} ago`;
    if(seconds<86400)return `Offline · Active ${Math.floor(seconds/3600)} hour${seconds<7200?"":"s"} ago`;
    if(seconds<604800)return `Offline · Active ${Math.floor(seconds/86400)} day${seconds<172800?"":"s"} ago`;
    return `Offline · Active ${new Date(value.endsWith?.("Z")?value:`${value}Z`).toLocaleDateString()}`;
  }

  function normalizeMessage(x){
    if(!x||typeof x!=="object")return null;
    return {
      id:Number(x.id),
      conversation_id:x.conversation_id==null?null:Number(x.conversation_id),
      sender_id:Number(x.sender_id??x.from_user_id),
      from_user_id:Number(x.from_user_id??x.sender_id),
      to_user_id:x.to_user_id==null?null:Number(x.to_user_id),
      content:String(x.content??""),
      message_type:x.attachment_mime?.startsWith?.("video/")?"video":x.message_type||"text",
      attachment_url:x.attachment_url||null,
      attachment_name:x.attachment_name||null,
      attachment_mime:x.attachment_mime||null,
      sticker:x.sticker||null,
      stickers:messageStickers(x.sticker),
      reaction_counts:x.reaction_counts||{},
      my_reaction:x.my_reaction||null,
      created_at:x.created_at||new Date().toISOString()
    };
  }

  function mergeMessages(items){
    const clean=(Array.isArray(items)?items:[items])
      .map(normalizeMessage)
      .filter(x=>x&&Number.isFinite(x.id)&&Number.isFinite(x.sender_id));

    setMessages(prev=>{
      const map=new Map();
      [...prev,...clean].forEach(x=>map.set(x.id,x));
      return [...map.values()].sort((a,b)=>{
        const da=Date.parse(a.created_at)||0;
        const db=Date.parse(b.created_at)||0;
        return da===db?a.id-b.id:da-db;
      });
    });
  }

  async function loadHistory(silent=false){
    if(!target?.id)return;
    try{
      const rows=await api(`/api/chat/${target.id}/messages`);
      if(Array.isArray(rows))mergeMessages(rows);
      onChanged?.();
    }catch(e){
      if(!silent)console.error("Cannot load chat history:",e);
    }
  }

  useEffect(()=>{
    setMessages([]);setSelectedStickers([]);setShowStickers(false);
    if(target?.id)loadHistory();
  },[target?.id]);

  useEffect(()=>{
    if(!target?.id)return;
    let stopped=false;
    async function loadPresence(){try{const d=await api(`/api/chat/presence/${target.id}`);if(!stopped)setPresence(d)}catch(e){console.error(e)}}
    loadPresence();const timer=setInterval(loadPresence,10000);
    return()=>{stopped=true;clearInterval(timer)};
  },[target?.id]);

  useEffect(()=>{
    endRef.current?.scrollIntoView?.({behavior:"smooth",block:"end"});
  },[messages.length,isOtherTyping]);

  // REST polling fallback: guarantees incoming messages even if WebSocket/proxy fails.
  useEffect(()=>{
    if(!target?.id)return;
    const timer=setInterval(()=>loadHistory(true),2500);
    return()=>clearInterval(timer);
  },[target?.id]);

  useEffect(()=>{
    let stopped=false;

    function connect(){
      if(stopped||!tok())return;
      let socket;
      try{
        socket=new WebSocket(`${WS}/api/chat/ws?token=${encodeURIComponent(tok())}`);
      }catch(e){
        setConnected(false);
        retryRef.current=setTimeout(connect,2000);
        return;
      }

      wsRef.current=socket;

      socket.onopen=()=>{
        if(stopped)return;
        setConnected(true);
        try{socket.send("ping")}catch{}
        clearInterval(pingRef.current);
        pingRef.current=setInterval(()=>{
          try{
            if(socket.readyState===WebSocket.OPEN)socket.send("ping");
          }catch{}
        },25000);
      };

      socket.onmessage=e=>{
        if(e.data==="pong")return;
        try{
          const data=JSON.parse(e.data);
          if(data?.type==="message_reaction"){
            setMessages(prev=>prev.map(m=>m.id===Number(data.message_id)?{...m,reaction_counts:data.reaction_counts||{},my_reaction:Number(data.reacting_user_id)===Number(me.id)?data.reaction:m.my_reaction}:m));
            return;
          }
          if(data?.type==="typing"){
            if(Number(data.from_user_id)===Number(target?.id)&&Number(data.to_user_id)===Number(me.id)){
              setIsOtherTyping(Boolean(data.is_typing));clearTimeout(typingHideRef.current);
              if(data.is_typing)typingHideRef.current=setTimeout(()=>setIsOtherTyping(false),2500);
            }
            return;
          }
          if(data?.type!=="message")return;

          const x=normalizeMessage(data);
          if(!x||!target?.id)return;

          const currentId=Number(target.id);
          const meId=Number(me.id);
          const belongs=
            (x.from_user_id===currentId&&x.to_user_id===meId)||
            (x.from_user_id===meId&&x.to_user_id===currentId)||
            (x.sender_id===currentId);

          if(belongs)mergeMessages(x);
          onChanged?.();
        }catch(err){
          console.error("Chat websocket message error:",err);
        }
      };

      socket.onerror=()=>{try{socket.close()}catch{}};
      socket.onclose=()=>{
        if(stopped)return;
        setConnected(false);
        clearInterval(pingRef.current);
        clearTimeout(retryRef.current);
        retryRef.current=setTimeout(connect,1800);
      };
    }

    connect();

    return()=>{
      stopped=true;
      clearInterval(pingRef.current);
      clearTimeout(retryRef.current);
      clearTimeout(typingStopRef.current);
      clearTimeout(typingHideRef.current);
      try{wsRef.current?.close()}catch{}
    };
  },[Number(me.id),Number(target?.id||0)]);

  async function send(){
    const value=text.trim();
    if(!target?.id||(!value&&!selectedStickers.length)||sending)return;

    setSending(true);
    setText("");
    const stickersToSend=[...selectedStickers];
    setSelectedStickers([]);setShowStickers(false);
    emitTyping(false);

    try{
      const result=await api(`/api/chat/${target.id}/messages`,{
        method:"POST",
        body:JSON.stringify({content:value,message_type:stickersToSend.length?"sticker":"text",sticker:stickersToSend.length?JSON.stringify(stickersToSend):null})
      });
      mergeMessages(result);
      await loadHistory(true);
      onChanged?.();
    }catch(e){
      console.error("Send message failed:",e);
      setText(value);
      setSelectedStickers(stickersToSend);
      alert(`Could not send message: ${e.message}`);
    }finally{
      setSending(false);
    }
  }

  function emitTyping(isTyping){
    try{if(target?.id!==me.id&&wsRef.current?.readyState===WebSocket.OPEN)wsRef.current.send(JSON.stringify({type:"typing",to_user_id:target.id,is_typing:isTyping}))}catch{}
  }
  function changeText(value){
    setText(value);clearTimeout(typingStopRef.current);emitTyping(Boolean(value.trim()));
    if(value.trim())typingStopRef.current=setTimeout(()=>emitTyping(false),1200);
  }

  async function uploadAttachment(file,forcedType){
    if(!target?.id||!file||sending)return;
    setSending(true);
    try{
      const fd=new FormData();fd.append("file",file);
      const uploaded=await api("/api/chat/upload",{method:"POST",body:fd});
      const result=await api(`/api/chat/${target.id}/messages`,{method:"POST",body:JSON.stringify({content:"",message_type:forcedType||uploaded.message_type,attachment_url:uploaded.url,attachment_name:uploaded.name,attachment_mime:uploaded.mime})});
      mergeMessages(result);onChanged?.();
    }catch(e){alert(`Could not send attachment: ${e.message}`)}finally{setSending(false)}
  }

  async function reactMessage(messageId,reaction){
    try{
      const d=await api(`/api/chat/messages/${messageId}/reaction`,{method:"POST",body:JSON.stringify({reaction})});
      setMessages(prev=>prev.map(m=>m.id===messageId?{...m,reaction_counts:d.reaction_counts||{},my_reaction:d.my_reaction}:m));
    }catch(e){alert(e.message)}
  }

  async function toggleRecording(){
    if(recording){recorderRef.current?.stop();return}
    try{
      const stream=await navigator.mediaDevices.getUserMedia({audio:true});
      const recorder=new MediaRecorder(stream);chunksRef.current=[];recorderRef.current=recorder;
      recorder.ondataavailable=e=>{if(e.data.size)chunksRef.current.push(e.data)};
      recorder.onstop=()=>{const blob=new Blob(chunksRef.current,{type:recorder.mimeType||"audio/webm"});stream.getTracks().forEach(t=>t.stop());setRecording(false);uploadAttachment(new File([blob],`voice-${Date.now()}.webm`,{type:blob.type}),"voice")};
      recorder.start();setRecording(true);
    }catch(e){alert("Microphone access is required to record voice messages.")}
  }

  if(!target)return <div className="card empty chat-empty">Choose someone to message.</div>;

  return <div className="chat card">
    <button className="chat-head profile-button" onClick={()=>open(target.id)}>
      <Avatar user={target}/>
      <div>
        <b>{target.name}</b>
        <div className={`presence-line small ${presence.online?"online":"offline"}`}><span className="presence-dot"/>{presence.online?"Online":lastActiveLabel(presence.last_seen_at)}</div>
      </div>
    </button>

    <div className="messages">
      {messages.map(x=><div key={x.id} className={`bubble ${x.sender_id===Number(me.id)?"mine":""} attachment-bubble`}>
        {x.message_type==="image"&&x.attachment_url&&<button className="chat-media-button" onClick={()=>setPreviewMedia({type:"image",url:asset(x.attachment_url),name:x.attachment_name})}><img className="chat-image" src={asset(x.attachment_url)} alt={x.attachment_name||"Image"}/><span className="media-hover-icon"><Maximize2 size={20}/></span></button>}
        {x.message_type==="video"&&x.attachment_url&&<div className="chat-video-wrap"><video className="chat-video" src={asset(x.attachment_url)} controls preload="metadata" playsInline/><button className="media-expand" onClick={()=>setPreviewMedia({type:"video",url:asset(x.attachment_url),name:x.attachment_name})}><Maximize2 size={16}/> Preview</button></div>}
        {x.message_type==="voice"&&x.attachment_url&&<audio className="chat-audio" controls src={asset(x.attachment_url)}/>}
        {x.message_type==="file"&&x.attachment_url&&<a className="chat-file" href={asset(x.attachment_url)} download={x.attachment_name}><FileText size={22}/><span>{x.attachment_name||"Download file"}</span><Download size={17}/></a>}
        {x.message_type==="sticker"?<div className={`message-with-sticker ${x.content&&x.sticker?"mixed":"sticker-only"}`}>{x.content&&x.sticker&&<span className="message-text">{x.content}</span>}<span className="message-stickers" role="img" aria-label="Stickers">{(x.stickers.length?x.stickers:messageStickers(x.sticker||x.content)).map((item,index)=><span className="message-sticker" key={`${item}-${index}`}>{item}</span>)}</span></div>:x.content&&<div>{x.content}</div>}
        <div className="message-reaction-control"><button className="message-react-trigger" title="React">{x.my_reaction?reactionInfo(x.my_reaction).emoji:"☺"}</button><div className="message-reaction-picker">{REACTIONS.map(r=><button key={r.key} title={r.label} onClick={()=>reactMessage(x.id,r.key)}>{r.emoji}</button>)}</div></div>
        {Object.keys(x.reaction_counts||{}).length>0&&<div className="message-reaction-summary">{Object.entries(x.reaction_counts).filter(([,n])=>n>0).map(([key,n])=><span key={key}>{reactionInfo(key).emoji}{n>1?n:""}</span>)}</div>}
      </div>)}
      {isOtherTyping&&<div className="typing-indicator"><span/><span/><span/><b>{target.name} is typing...</b></div>}
      <div ref={endRef}/>
    </div>

    <div className="chat-input">
      <label className="chat-tool" title="Send image or video"><ImageIcon size={19}/><input hidden type="file" accept="image/*,video/*" onChange={e=>{const f=e.target.files?.[0];uploadAttachment(f,f?.type.startsWith("video/")?"video":"image");e.target.value=""}}/></label>
      <label className="chat-tool" title="Send file"><Paperclip size={19}/><input hidden type="file" onChange={e=>{uploadAttachment(e.target.files?.[0],"file");e.target.value=""}}/></label>
      <button type="button" className={`chat-tool ${recording?"recording":""}`} title={recording?"Stop recording":"Record voice"} onClick={toggleRecording}>{recording?<Square size={17}/>:<Mic size={19}/>}</button>
      <div className="chat-sticker-control"><button type="button" className={`chat-tool ${showStickers?"active":""}`} title="Stickers" onClick={()=>setShowStickers(!showStickers)}><Smile size={20}/></button>{showStickers&&<div className="sticker-library chat-sticker-library"><div className="sticker-library-head"><div><b>Stickers</b><small>Choose one or more stickers</small></div><button type="button" className="icon-btn" onClick={()=>setShowStickers(false)}><X size={18}/></button></div><div className="sticker-grid">{STICKERS.map((item,index)=><button type="button" key={`chat-${item}-${index}`} className={selectedStickers.includes(item)?"selected":""} onClick={()=>{setSelectedStickers(current=>current.length<12?[...current,item]:current);emitTyping(Boolean(text.trim()))}}>{item}</button>)}</div></div>}</div>
      <div className={`chat-compose-field ${selectedStickers.length?"has-sticker":""}`}>
        <input
          className={text?"has-text":""}
          style={text?{width:`${Math.min(42,Math.max(3,text.length+1))}ch`}:undefined}
          value={text}
          placeholder={`Message ${target.name}...`}
          onChange={e=>changeText(e.target.value)}
          onKeyDown={e=>{
            if(e.key==="Enter"&&!e.shiftKey){
              e.preventDefault();
              send();
            }
          }}
        />
        {selectedStickers.length>0&&<div className="chat-sticker-previews" title="Selected stickers">{selectedStickers.map((item,index)=><span className="chat-sticker-preview" key={`${item}-${index}`}><i>{item}</i><button type="button" onClick={()=>setSelectedStickers(current=>current.filter((_,position)=>position!==index))} aria-label="Remove sticker"><X size={10}/></button></span>)}</div>}
        <span className="chat-compose-spacer"/>
      </div>
      <button type="button" className="primary" disabled={sending||(!text.trim()&&!selectedStickers.length)} onClick={send}>
        <Send size={18}/>
      </button>
    </div>
    {previewMedia&&<MediaPreview media={previewMedia} onClose={()=>setPreviewMedia(null)}/>} 
  </div>
}

function SettingsPage({user,onUserUpdated,theme="dark",onThemeChange,language="en",onLanguageChange}){
  const[f,setF]=useState({current_password:"",new_password:"",confirm_password:""}),[msg,setMsg]=useState(""),[err,setErr]=useState(""),[busy,setBusy]=useState(false);
  const[username,setUsername]=useState(user.username||"");
  const[usernameStatus,setUsernameStatus]=useState(null);
  const[usernameMsg,setUsernameMsg]=useState("");
  const[usernameErr,setUsernameErr]=useState("");
  const[usernameBusy,setUsernameBusy]=useState(false);

  useEffect(()=>{api("/api/users/me/username-status").then(setUsernameStatus).catch(e=>setUsernameErr(e.message))},[user.id]);

  async function submit(e){
    e.preventDefault();
    setMsg("");setErr("");

    if(f.new_password.length<8){setErr("New password must be at least 8 characters.");return}
    if(f.new_password!==f.confirm_password){setErr("Password confirmation does not match.");return}

    setBusy(true);
    try{
      const d=await api("/api/users/me/password",{
        method:"PUT",
        body:JSON.stringify({current_password:f.current_password,new_password:f.new_password})
      });
      setMsg(d.message||"Password changed successfully.");
      setF({current_password:"",new_password:"",confirm_password:""});
    }catch(e){setErr(e.message)}
    finally{setBusy(false)}
  }

  async function submitUsername(e){
    e.preventDefault();setUsernameMsg("");setUsernameErr("");
    const value=username.trim().toLowerCase();
    if(!/^[a-z0-9._]{3,80}$/.test(value)){setUsernameErr("Use 3–80 letters, numbers, dots or underscores.");return}
    setUsernameBusy(true);
    try{
      const d=await api("/api/users/me/username",{method:"PUT",body:JSON.stringify({username:value})});
      setUsernameStatus(d);setUsername(d.username);setUsernameMsg(d.message);onUserUpdated?.(d.user);
    }catch(e){setUsernameErr(e.message)}finally{setUsernameBusy(false)}
  }

  return <div className="card settings-page">
    <h2>Settings</h2>
    <div className="settings-profile"><Avatar user={user} size={52}/><div><b>{user.name}</b><div className="muted">@{user.username}</div></div></div>
    <div className="settings-section appearance-settings">
      <h3>Appearance</h3>
      <p className="muted small">Choose how SocialN looks on this browser.</p>
      <div className="theme-options" role="radiogroup" aria-label="Color theme">
        <button type="button" role="radio" aria-checked={theme==="light"} className={`theme-option ${theme==="light"?"selected":""}`} onClick={()=>onThemeChange?.("light")}><Sun size={22}/><span><b>Light</b><small>Bright background</small></span><i>{theme==="light"?"✓":""}</i></button>
        <button type="button" role="radio" aria-checked={theme==="dark"} className={`theme-option ${theme==="dark"?"selected":""}`} onClick={()=>onThemeChange?.("dark")}><Moon size={22}/><span><b>Dark</b><small>Easy on the eyes</small></span><i>{theme==="dark"?"✓":""}</i></button>
      </div>
    </div>
    <div className="settings-section language-settings">
      <h3>Language</h3>
      <p className="muted small">Choose the language used across SocialN.</p>
      <LanguagePicker value={language} onChange={onLanguageChange}/>
    </div>
    <div className="settings-section">
      <h3>Change username</h3>
      <p className="muted small">Your profile address will become localhost:5173/{username||"username"}. You can change your username only once every 30 days.</p>
      <form onSubmit={submitUsername}>
        <label>Username<input value={username} disabled={usernameStatus&&!usernameStatus.can_change} onChange={e=>setUsername(e.target.value)} autoComplete="username"/></label>
        {usernameStatus&&!usernameStatus.can_change&&<div className="username-cooldown">You can change it again on <b>{new Date(usernameStatus.next_change_at).toLocaleString()}</b>.</div>}
        {usernameErr&&<div className="error">{usernameErr}</div>}
        {usernameMsg&&<div className="success-notice">{usernameMsg}</div>}
        <button className="primary" disabled={usernameBusy||!usernameStatus?.can_change||username.trim().toLowerCase()===user.username.toLowerCase()}>{usernameBusy?"Updating...":"Change username"}</button>
      </form>
    </div>
    <div className="settings-section">
      <h3>Change password</h3>
      <form onSubmit={submit}>
        <label>Current password<input type="password" autoComplete="current-password" value={f.current_password} onChange={e=>setF({...f,current_password:e.target.value})}/></label>
        <label>New password<input type="password" autoComplete="new-password" value={f.new_password} onChange={e=>setF({...f,new_password:e.target.value})}/></label>
        <label>Confirm new password<input type="password" autoComplete="new-password" value={f.confirm_password} onChange={e=>setF({...f,confirm_password:e.target.value})}/></label>
        {err&&<div className="error">{err}</div>}
        {msg&&<div className="success-notice">{msg}</div>}
        <button className="primary" disabled={busy}>{busy?"Updating...":"Change password"}</button>
      </form>
    </div>
  </div>
}
function App(){const[user,setUser]=useState(null),[view,setView]=useState("home"),[feed,setFeed]=useState([]),[profile,setProfile]=useState(null),[friends,setFriends]=useState([]),[requests,setRequests]=useState([]),[suggestions,setSuggestions]=useState([]),[target,setTarget]=useState(null),[conversations,setConversations]=useState([]),[notifs,setNotifs]=useState([]),[unread,setUnread]=useState(0),[drop,setDrop]=useState(false),[search,setSearch]=useState(""),[results,setResults]=useState([]);useEffect(()=>{if(tok())api("/api/users/me").then(setUser)},[]);useEffect(()=>{if(!user)return;refresh();const w=new WebSocket(`${WS}/api/notifications/ws?token=${tok()}`);w.onopen=()=>w.send("ready");w.onmessage=()=>loadN();return()=>w.close()},[user?.id]);async function refresh(){loadFeed();setFriends(await api("/api/friends"));setRequests(await api("/api/friends/requests"));setSuggestions(await api("/api/users/suggestions/people"));loadN();loadC()}async function loadFeed(){try{const rows=await api("/api/posts");setFeed(Array.isArray(rows)?rows:[])}catch(e){console.error("Feed load failed",e);setFeed([])}}async function loadC(){try{const rows=await api("/api/chat/conversations");setConversations((Array.isArray(rows)?rows:[]).filter(c=>c&&c.user&&c.user.id))}catch(e){console.error("Conversation load failed",e);setConversations([])}}async function loadN(){const d=await api("/api/notifications");setNotifs(d.items);setUnread(d.unread_count)}async function open(id){const d=await api(`/api/users/${id}/profile`);setProfile(d);setView("profile");setDrop(false)}async function reload(id){await open(id);refresh()}function message(u){setTarget(u);setView("chat");loadC()}async function q(v){setSearch(v);setResults(v.trim()?await api(`/api/users/search?q=${encodeURIComponent(v)}`):[])}async function read(n){if(!n.is_read)await api(`/api/notifications/${n.id}/read`,{method:"POST"});if(n.type==="new_message"&&n.actor)message(n.actor);else if(n.type==="friend_request")setView("friends");else if(n.actor)open(n.actor.id);setDrop(false);loadN()}if(!user)return <Login onLogin={setUser}/>;return <div><header className="topbar"><div className="brand" onClick={()=>setView("home")}>Social<span>N</span></div><div className="search"><Search/><input value={search} onChange={e=>q(e.target.value)} placeholder="Search SocialN..."/>{results.length>0&&<div className="search-results">{results.map(u=><button key={u.id} onClick={()=>{open(u.id);setResults([]);setSearch("")}}><Avatar user={u}/><span>{u.name}<small>@{u.username}</small></span></button>)}</div>}</div><div className="top-actions"><button onClick={()=>setView("home")}><Home/></button><button onClick={()=>setView("friends")}><Users/></button><button onClick={()=>setView("chat")}><MessageCircle/></button><div className="notif-wrap"><button className="notification-btn" onClick={()=>setDrop(!drop)}><Bell/>{unread>0&&<span className="badge">{unread}</span>}</button>{drop&&<div className="notif-dropdown"><div className="notif-dropdown-head"><b>Notifications</b><button onClick={async()=>{await api("/api/notifications/read-all",{method:"POST"});loadN()}}>Mark all read</button></div><div className="notif-scroll">{notifs.slice(0,20).map(n=><button className={`notification-row ${n.is_read?"":"unread"}`} key={n.id} onClick={()=>read(n)}><Avatar user={n.actor}/><div className="notification-content">{n.message}<small>{new Date(n.created_at).toLocaleString()}</small></div></button>)}</div></div>}</div><button onClick={()=>setView("settings")}><Settings/></button><button onClick={()=>{localStorage.removeItem("socialn_token");setUser(null)}}><LogOut/></button></div></header><div className="layout"><aside className="sidebar"><button className="side-user" onClick={()=>open(user.id)}><Avatar user={user}/><b>{user.name}</b></button><button onClick={()=>setView("home")}><Home/> Home</button><button onClick={()=>open(user.id)}><Users/> Profile</button><button onClick={()=>setView("friends")}><UserCheck/> Friends {requests.length>0&&<span className="side-badge">{requests.length}</span>}</button><button onClick={()=>setView("chat")}><MessageCircle/> Messages</button><button onClick={()=>setView("settings")}><Settings/> Settings</button></aside><main className="main">{view==="home"&&<>
  <PostComposer onCreated={p=>setFeed(v=>[p,...v])}/>
  {feed.length===0?<div className="card empty">No posts yet. Create the first post.</div>:feed.map(p=><PostCard key={p.id} post={p} me={user} onOpenProfile={open} onUpdated={updated=>setFeed(v=>v.map(x=>x.id===updated.id?updated:x))} onDeleted={id=>setFeed(v=>v.filter(x=>x.id!==id))}/>)}
</>}{view==="profile"&&profile&&<Profile p={profile} me={user} reload={reload} message={message} open={open}/>} {view==="friends"&&<div className="friends-page"><div className="card friends-section"><h2>Friend requests</h2>{requests.map(r=><div className="request-row" key={r.id}><Avatar user={r.user} onClick={()=>open(r.user.id)}/><button className="name-block" onClick={()=>open(r.user.id)}><b>{r.user.name}</b></button><button className="primary" onClick={async()=>{await api(`/api/friends/${r.id}/accept`,{method:"POST"});refresh()}}>Confirm</button><button className="secondary" onClick={async()=>{await api(`/api/friends/${r.id}/reject`,{method:"POST"});refresh()}}>Delete</button></div>)}</div><div className="card friends-section"><h2>Your friends</h2><div className="people-grid">{friends.map(u=><div className="person" key={u.id}><Avatar user={u} onClick={()=>open(u.id)}/><button className="name-link" onClick={()=>open(u.id)}>{u.name}</button><button className="secondary" onClick={()=>message(u)}>Message</button></div>)}</div></div><div className="card friends-section"><h2>People you may know</h2><div className="people-grid">{suggestions.map(u=><div className="person" key={u.id}><Avatar user={u} onClick={()=>open(u.id)}/><button className="name-link" onClick={()=>open(u.id)}>{u.name}</button><small>{u.mutual_friends_count} mutual friends</small><button className="primary" onClick={async()=>{await api(`/api/friends/${u.id}`,{method:"POST"});refresh()}}>Add friend</button></div>)}</div></div></div>} {view==="chat"&&<div className="chat-layout"><div className="conversation-list card"><div className="conversation-title">Messages</div>{conversations.filter(c=>c?.user?.id).map(c=><button key={`c-${c.id}`} className={Number(target?.id)===Number(c.user.id)?"active":""} onClick={()=>setTarget(c.user)}><Avatar user={c.user}/><span>{c.user.name||c.user.username}<small>{c.last_message||`@${c.user.username}`}</small></span></button>)}{friends.filter(u=>u?.id&&!conversations.some(c=>Number(c?.user?.id)===Number(u.id))).map(u=><button key={`f-${u.id}`} className={Number(target?.id)===Number(u.id)?"active":""} onClick={()=>setTarget(u)}><Avatar user={u}/><span>{u.name}<small>Start a conversation</small></span></button>)}</div><Chat me={user} target={target} open={open} onChanged={loadC}/></div>} {view==="notifications"&&<div className="card notifications-page">{notifs.map(n=><button className="notification-row" key={n.id} onClick={()=>read(n)}>{n.message}</button>)}</div>} {view==="settings"&&<SettingsPage user={user}/>} </main></div></div>}
const RESERVED_PATHS=new Set(["settings","friends","messages","notifications"]);
const currentPath=()=>decodeURIComponent(window.location.pathname.replace(/^\/+|\/+$/g,""));

function RoutedApp(){
  const[user,setUser]=useState(null),[view,setView]=useState("home"),[feed,setFeed]=useState([]),[profile,setProfile]=useState(null),[friends,setFriends]=useState([]),[requests,setRequests]=useState([]),[suggestions,setSuggestions]=useState([]),[target,setTarget]=useState(null),[conversations,setConversations]=useState([]),[notifs,setNotifs]=useState([]),[unread,setUnread]=useState(0),[messageUnread,setMessageUnread]=useState(0),[drop,setDrop]=useState(false),[search,setSearch]=useState(""),[results,setResults]=useState([]),[routeError,setRouteError]=useState("");
  const[theme,setTheme]=useState(()=>localStorage.getItem("socialn_theme")||"dark");
  const[language,setLanguage]=useState(()=>localStorage.getItem("socialn_language")||"vi");

  useEffect(()=>{document.documentElement.dataset.theme=theme;document.documentElement.style.colorScheme=theme;localStorage.setItem("socialn_theme",theme)},[theme]);
  useEffect(()=>{setSiteLanguage(language)},[language]);

  function setRoute(path,nextView,{replace=false}={}){
    const normalized=path.startsWith("/")?path:`/${path}`;
    if(window.location.pathname!==normalized)window.history[replace?"replaceState":"pushState"]({},"",normalized);
    setView(nextView);setDrop(false);setRouteError("");
  }

  async function loadFeed(){try{const rows=await api("/api/posts");setFeed(Array.isArray(rows)?rows:[])}catch(e){console.error(e);setFeed([])}}
  async function loadC(){try{const rows=await api("/api/chat/conversations");setConversations((Array.isArray(rows)?rows:[]).filter(c=>c?.user?.id))}catch(e){console.error(e);setConversations([])}}
  async function loadN(){try{const d=await api("/api/notifications");setNotifs(d.items||[]);setUnread(d.unread_count||0)}catch(e){console.error(e)}}
  async function loadMessageUnread(){try{const d=await api("/api/chat/unread-count");setMessageUnread(d.unread_count||0)}catch(e){console.error(e)}}
  async function refresh(){loadFeed();loadN();loadC();loadMessageUnread();try{const [f,r,s]=await Promise.all([api("/api/friends"),api("/api/friends/requests"),api("/api/users/suggestions/people")]);setFriends(f);setRequests(r);setSuggestions(s)}catch(e){console.error(e)}}

  async function openProfile(id,{replace=false}={}){
    try{const d=await api(`/api/users/${id}/profile`);setProfile(d);setRoute(`/${encodeURIComponent(d.user.username)}`,"profile",{replace})}catch(e){setRouteError(e.message)}
  }
  async function openUsername(username,{replace=false}={}){
    try{const d=await api(`/api/users/username/${encodeURIComponent(username)}/profile`);setProfile(d);setRoute(`/${encodeURIComponent(d.user.username)}`,"profile",{replace})}catch(e){setView("not_found");setRouteError(e.message)}
  }
  async function reloadProfile(id){try{const d=await api(`/api/users/${id}/profile`);setProfile(d);setView("profile");refresh()}catch(e){setRouteError(e.message)}}
  function go(path,nextView){setRoute(path,nextView)}
  function message(u){setTarget(u);setRoute(`/messages/${encodeURIComponent(u.username)}`,"chat");loadC()}

  async function resolvePath(replace=false){
    const path=currentPath();
    if(!path){setRoute("/","home",{replace});return}
    const [head,second]=path.split("/");
    if(head==="settings"){setView("settings");return}
    if(head==="friends"){setView("friends");return}
    if(head==="notifications"){setView("notifications");return}
    if(head==="messages"){
      setView("chat");
      if(second){try{const d=await api(`/api/users/username/${encodeURIComponent(second)}/profile`);setTarget(d.user)}catch(e){setRouteError(e.message)}}
      return;
    }
    if(!RESERVED_PATHS.has(head))await openUsername(head,{replace:true});
  }

  useEffect(()=>{if(tok())api("/api/users/me").then(setUser).catch(()=>{localStorage.removeItem("socialn_token");window.history.replaceState({},"","/")})},[]);
  useEffect(()=>{if(!user)return;refresh();resolvePath(true);const onPop=()=>resolvePath(true);window.addEventListener("popstate",onPop);const w=new WebSocket(`${WS}/api/notifications/ws?token=${encodeURIComponent(tok())}`);w.onopen=()=>w.send("ready");w.onmessage=()=>{loadN();loadMessageUnread();loadC()};return()=>{window.removeEventListener("popstate",onPop);w.close()}},[user?.id]);

  async function query(v){setSearch(v);try{setResults(v.trim()?await api(`/api/users/search?q=${encodeURIComponent(v)}`):[])}catch{setResults([])}}
  async function read(n){if(!n.is_read)await api(`/api/notifications/${n.id}/read`,{method:"POST"});if(n.type==="new_message"&&n.actor)message(n.actor);else if(n.type==="friend_request")go("/friends","friends");else if(n.actor)openProfile(n.actor.id);setDrop(false);loadN()}
  function logout(){localStorage.removeItem("socialn_token");window.history.replaceState({},"","/");setUser(null)}

  if(!user)return <Login language={language} onLanguageChange={setLanguage} onLogin={u=>{setUser(u);window.history.replaceState({},"","/")}}/>;
  return <div><ConfirmHost/>
    <header className="topbar"><div className="brand" onClick={()=>go("/","home")}>Social<span>N</span></div><div className="search"><Search/><input value={search} onChange={e=>query(e.target.value)} placeholder="Search SocialN..."/>{results.length>0&&<div className="search-results">{results.map(u=><button key={u.id} onClick={()=>{openProfile(u.id);setResults([]);setSearch("")}}><Avatar user={u}/><span>{u.name}<small>@{u.username}</small></span></button>)}</div>}</div>
      <div className="top-actions"><button onClick={()=>go("/","home")}><Home/></button><button onClick={()=>go("/friends","friends")}><Users/></button><button className="message-icon-btn" onClick={()=>go("/messages","chat")}><MessageCircle/>{messageUnread>0&&<span className="badge">{messageUnread>99?"99+":messageUnread}</span>}</button><div className="notif-wrap"><button className="notification-btn" onClick={()=>setDrop(!drop)}><Bell/>{unread>0&&<span className="badge">{unread}</span>}</button>{drop&&<div className="notif-dropdown"><div className="notif-dropdown-head"><b>Notifications</b><button onClick={async()=>{await api("/api/notifications/read-all",{method:"POST"});loadN()}}>Mark all read</button></div><div className="notif-scroll">{notifs.slice(0,20).map(n=><button className={`notification-row ${n.is_read?"":"unread"}`} key={n.id} onClick={()=>read(n)}><Avatar user={n.actor}/><div className="notification-content">{n.message}<small>{new Date(n.created_at).toLocaleString()}</small></div></button>)}</div></div>}</div><button onClick={()=>go("/settings","settings")}><Settings/></button><button onClick={logout}><LogOut/></button></div>
    </header>
    <div className="layout"><aside className="sidebar"><button className="side-user" onClick={()=>openProfile(user.id)}><Avatar user={user}/><b>{user.name}</b></button><button onClick={()=>go("/","home")}><Home/> Home</button><button onClick={()=>openProfile(user.id)}><Users/> Profile</button><button onClick={()=>go("/friends","friends")}><UserCheck/> Friends {requests.length>0&&<span className="side-badge">{requests.length}</span>}</button><button onClick={()=>go("/messages","chat")}><MessageCircle/> Messages</button><button onClick={()=>go("/settings","settings")}><Settings/> Settings</button></aside>
      <main className={`main ${view==="chat"?"chat-main":""}`}>
        {routeError&&<div className="error">{routeError}</div>}
        {view==="home"&&<><PostComposer onCreated={p=>setFeed(v=>[p,...v])}/>{feed.length===0?<div className="card empty">No posts yet. Create the first post.</div>:feed.map(p=><PostCard key={p.id} post={p} me={user} onOpenProfile={openProfile} onUpdated={updated=>setFeed(v=>v.map(x=>x.id===updated.id?updated:x))} onDeleted={id=>setFeed(v=>v.filter(x=>x.id!==id))}/>)}</>}
        {view==="profile"&&profile&&<Profile data={profile} me={user} reload={reloadProfile} message={message} open={openProfile}/>} 
        {view==="friends"&&<div className="friends-page"><div className="card friends-section"><h2>Friend requests</h2>{requests.length===0&&<div className="muted">No pending requests.</div>}{requests.map(r=><div className="request-row" key={r.id}><Avatar user={r.user} onClick={()=>openProfile(r.user.id)}/><button className="name-block" onClick={()=>openProfile(r.user.id)}><b>{r.user.name}</b></button><button className="primary" onClick={async()=>{await api(`/api/friends/${r.id}/accept`,{method:"POST"});refresh()}}>Confirm</button><button className="secondary" onClick={async()=>{await api(`/api/friends/${r.id}/reject`,{method:"POST"});refresh()}}>Delete</button></div>)}</div><div className="card friends-section"><h2>Your friends</h2><div className="people-grid">{friends.map(u=><div className="person" key={u.id}><Avatar user={u} onClick={()=>openProfile(u.id)}/><button className="name-link" onClick={()=>openProfile(u.id)}>{u.name}</button><button className="secondary" onClick={()=>message(u)}>Message</button></div>)}</div></div><div className="card friends-section"><h2>People you may know</h2><div className="people-grid">{suggestions.map(u=><div className="person" key={u.id}><Avatar user={u} onClick={()=>openProfile(u.id)}/><button className="name-link" onClick={()=>openProfile(u.id)}>{u.name}</button><small>{u.mutual_friends_count} mutual friends</small><button className="primary" onClick={async()=>{await api(`/api/friends/${u.id}`,{method:"POST"});refresh()}}>Add friend</button></div>)}</div></div></div>}
        {view==="chat"&&<div className="chat-layout"><div className="conversation-list card"><div className="conversation-title">Messages</div>
          {conversations.filter(c=>Number(c.user.id)===Number(user.id)).map(c=><ConversationRow key={c.id} conversation={c} personalStorage active={Number(target?.id)===Number(user.id)} onOpen={()=>message(user)} onChanged={loadC} onDeleted={()=>{setTarget(null);setRoute("/messages","chat")}}/>)}
          {!conversations.some(c=>Number(c.user.id)===Number(user.id))&&<button className="self-vault" onClick={()=>message(user)}><Avatar user={user}/><span><b>{user.name} (You)</b><small>Personal storage</small></span></button>}
          {conversations.filter(c=>Number(c.user.id)!==Number(user.id)).map(c=><ConversationRow key={c.id} conversation={c} active={Number(target?.id)===Number(c.user.id)} onOpen={()=>message(c.user)} onChanged={loadC} onDeleted={c=>{if(Number(target?.id)===Number(c.user.id)){setTarget(null);setRoute("/messages","chat")}}}/>)}
        </div><Chat me={user} target={target} open={openProfile} onChanged={()=>{loadC();loadMessageUnread()}}/></div>}
        {view==="notifications"&&<div className="card notifications-page">{notifs.map(n=><button className="notification-row" key={n.id} onClick={()=>read(n)}>{n.message}</button>)}</div>}
        {view==="settings"&&<SettingsPage user={user} onUserUpdated={setUser} theme={theme} onThemeChange={setTheme} language={language} onLanguageChange={setLanguage}/>} 
        {view==="not_found"&&<div className="card empty"><h2>Page not found</h2><button className="primary" onClick={()=>go("/","home")}>Go home</button></div>}
      </main>
    </div>
  </div>
}

createRoot(document.getElementById("root")).render(<ErrorBoundary><RoutedApp/></ErrorBoundary>);
