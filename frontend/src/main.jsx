import React,{Component,useEffect,useRef,useState}from"react";import{createRoot}from"react-dom/client";import{QueryClientProvider,useQueryClient}from"@tanstack/react-query";import{BrowserRouter,useLocation,useNavigate}from"react-router-dom";import{Search,Home,Users,UsersRound,MessageCircle,Bell,Settings,Image as ImageIcon,ThumbsUp,MessageSquare,Share2,Send,LogOut,Camera,UserPlus,UserCheck,ShieldBan,Menu,X,Check,MoreHorizontal,MoreVertical,Edit2,Trash2,Pin,Archive,Paperclip,Mic,Square,FileText,Download,Maximize2,Sun,Moon,Languages,Smile,History,Reply,Info,Copy,Volume2,Link2,Bookmark,EyeOff,Star,Clock3,UserMinus}from"lucide-react";import{LANGUAGES,setSiteLanguage,translate}from"./i18n";import{API_BASE_URL as API,WS_BASE_URL as WS,apiClient as api,assetUrl as asset}from"./services/api";import{authService}from"./services/auth";import{createAuthenticatedSocket}from"./services/websocket";import{NOTIFICATION_DEFAULTS as MESSAGE_NOTIFICATION_DEFAULTS,useNotificationPreferences}from"./hooks/useNotificationPreferences";import{queryClient}from"./query/client";import{FeedPage}from"./features/feed/FeedPage";import{ProfilePage}from"./features/profile/ProfilePage";import{MessagesPage}from"./features/messages/MessagesPage";import{GroupsModule}from"./features/groups/GroupsModule";import{SettingsModule}from"./features/settings/SettingsModule";import"./styles.css";
const tok=authService.token;
const TIMEZONES=[
  ["auto","Automatic (device)"],["UTC","UTC"],["Asia/Ho_Chi_Minh","Vietnam — Hanoi/Ho Chi Minh City (UTC+7)"],
  ["Asia/Bangkok","Thailand — Bangkok (UTC+7)"],["Asia/Shanghai","China — Beijing/Shanghai (UTC+8)"],
  ["Asia/Tokyo","Japan — Tokyo (UTC+9)"],["Asia/Seoul","South Korea — Seoul (UTC+9)"],
  ["Asia/Singapore","Singapore (UTC+8)"],["Asia/Kolkata","India — Kolkata (UTC+5:30)"],
  ["Europe/London","United Kingdom — London"],["Europe/Paris","Central Europe — Paris"],
  ["America/New_York","USA — New York"],["America/Chicago","USA — Chicago"],
  ["America/Denver","USA — Denver"],["America/Los_Angeles","USA — Los Angeles"],["Australia/Sydney","Australia — Sydney"]
];
const selectedTimeZone=()=>{const value=localStorage.getItem("socialn_timezone")||"auto";return value==="auto"?undefined:value};
const instantDate=value=>{if(!value)return null;const text=String(value);return new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(text)?text:`${text}Z`)};
const formatDateTime=value=>{const date=instantDate(value);return date&&!Number.isNaN(date.getTime())?new Intl.DateTimeFormat(undefined,{dateStyle:"medium",timeStyle:"medium",timeZone:selectedTimeZone()}).format(date):""};
const formatDate=value=>{const date=instantDate(value);return date&&!Number.isNaN(date.getTime())?new Intl.DateTimeFormat(undefined,{dateStyle:"medium",timeZone:selectedTimeZone()}).format(date):""};
const REACTIONS=[{key:"like",emoji:"👍",label:"Like"},{key:"love",emoji:"❤️",label:"Love"},{key:"haha",emoji:"😂",label:"Haha"},{key:"wow",emoji:"😮",label:"Wow"},{key:"sad",emoji:"😢",label:"Sad"},{key:"angry",emoji:"😡",label:"Angry"}];
const STICKERS=["😀","😂","🥰","😍","😎","🥳","🤩","🤗","🤔","😴","😭","😡","👍","👏","🙏","💪","❤️","💖","🔥","🎉","✨","🌈","🐶","🐱","🐼","🦊","🐸","🦄","🍕","🍰","☕","⚽","🎮","🚀","🌻","🎁"];
function messageStickers(value){if(!value)return[];try{const parsed=JSON.parse(value);return Array.isArray(parsed)?parsed.filter(x=>typeof x==="string").slice(0,24):[value]}catch{return[value]}}
function isEmojiOnlyMessage(value){return Boolean(value?.trim())&&/^(?:\p{Extended_Pictographic}|\p{Emoji_Presentation}|\p{Emoji_Modifier}|\uFE0F|\u200D)+$/u.test(value.trim())}
const reactionInfo=key=>REACTIONS.find(x=>x.key===key)||REACTIONS[0];

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
  const neutral=dialog.variant==="confirm";
  return <div className="modal-backdrop confirm-dialog-backdrop" role="presentation" onMouseDown={()=>finish(false)}><div className={`confirm-dialog ${neutral?"confirm-dialog-neutral":""}`} role="alertdialog" aria-modal="true" aria-labelledby="confirm-dialog-title" aria-describedby="confirm-dialog-description" onMouseDown={e=>e.stopPropagation()}>
    <div className="confirm-dialog-icon">{neutral?<Check size={25}/>:<Trash2 size={25}/>}</div>
    <div className="confirm-dialog-copy"><h3 id="confirm-dialog-title">{dialog.title||"Are you sure?"}</h3><p id="confirm-dialog-description">{dialog.message}</p>{dialog.detail&&<div className="confirm-dialog-detail">{dialog.detail}</div>}</div>
    <div className="confirm-dialog-actions"><button className="secondary" autoFocus onClick={()=>finish(false)}>{dialog.cancelLabel||"Cancel"}</button><button className={neutral?"primary":"danger confirm-danger"} onClick={()=>finish(true)}>{dialog.confirmLabel||(neutral?"Confirm":"Delete")}</button></div>
  </div></div>
}
function Avatar({user,size=42,onClick}){return user?.avatar_url?<img className="avatar clickable" style={{width:size,height:size}} src={asset(user.avatar_url)} onClick={onClick}/>:<div className="avatar avatar-fallback clickable" style={{width:size,height:size}} onClick={onClick}>{(user?.name||"?")[0]}</div>}
function MetroMessageToasts({items,onOpen,onDismiss}){if(!items.length)return null;return <div className="metro-toast-stack" aria-live="polite" aria-label="New notifications">{items.map(item=>{const activity=item.kind==="activity",avatar=activity?item.actor:{name:item.conversation_name,avatar_url:item.conversation_avatar_url};return <article className={`metro-message-toast ${activity?"metro-activity-toast":""}`} key={item.toastId} style={{"--toast-duration":`${item.duration}ms`}}><button className="metro-toast-main" onClick={()=>onOpen(item)}><Avatar user={avatar||{name:"SocialN"}} size={48}/><span><small>{activity?item.categoryLabel:item.is_group?`${item.actor?.name||"Someone"} · ${item.conversation_name}`:"NEW MESSAGE"}</small><b>{activity?item.actor?.name||"SocialN":item.is_group?item.conversation_name:item.actor?.name||item.conversation_name}</b><em>{activity?item.displayMessage:item.displayPreview}</em></span></button><button className="metro-toast-close" aria-label="Dismiss notification" onClick={()=>onDismiss(item.toastId)}><X size={18}/></button><i className="metro-toast-timer"/></article>})}</div>}
function LanguagePicker({value,onChange,compact=false}){return <div className={`language-picker ${compact?"compact":""}`}><Languages size={18}/><select value={value} onChange={e=>onChange(e.target.value)} aria-label="Language">{LANGUAGES.map(language=><option key={language.code} value={language.code}>{language.label}</option>)}</select></div>}
const AUTH_COPY={
  en:{tagline:"Connect with what matters to you.",loginTitle:"Log in to SocialN",registerTitle:"Create your SocialN account",email:"Email address",password:"Password",name:"Full name",username:"Username",login:"Log in",register:"Create account",forgot:"Forgot password?",newAccount:"Create new account",back:"Already have an account? Log in",recovery:"Password recovery is not available yet.",community:"Share moments",chat:"Stay connected",language:"Choose language",lightMode:"Light mode",darkMode:"Dark mode"},
  vi:{tagline:"Kết nối những điều bạn yêu thích.",loginTitle:"Đăng nhập vào SocialN",registerTitle:"Tạo tài khoản SocialN",email:"Địa chỉ email",password:"Mật khẩu",name:"Họ và tên",username:"Tên người dùng",login:"Đăng nhập",register:"Tạo tài khoản",forgot:"Quên mật khẩu?",newAccount:"Tạo tài khoản mới",back:"Đã có tài khoản? Đăng nhập",recovery:"Tính năng khôi phục mật khẩu chưa khả dụng.",community:"Chia sẻ khoảnh khắc",chat:"Luôn kết nối",language:"Chọn ngôn ngữ",lightMode:"Chế độ sáng",darkMode:"Chế độ tối"},
  ko:{tagline:"소중한 사람과 순간을 발견하세요.",loginTitle:"SocialN에 로그인",registerTitle:"SocialN 계정 만들기",email:"이메일 주소",password:"비밀번호",name:"이름",username:"사용자 이름",login:"로그인",register:"계정 만들기",forgot:"비밀번호를 잊으셨나요?",newAccount:"새 계정 만들기",back:"계정이 있으신가요? 로그인",recovery:"비밀번호 복구 기능은 아직 제공되지 않습니다.",community:"순간을 공유하세요",chat:"계속 연결하세요",language:"언어 선택",lightMode:"라이트 모드",darkMode:"다크 모드"},
  ja:{tagline:"大切な人や瞬間を見つけよう。",loginTitle:"SocialNにログイン",registerTitle:"SocialNアカウントを作成",email:"メールアドレス",password:"パスワード",name:"氏名",username:"ユーザー名",login:"ログイン",register:"アカウントを作成",forgot:"パスワードを忘れた場合",newAccount:"新しいアカウントを作成",back:"アカウントをお持ちですか？ ログイン",recovery:"パスワード回復はまだ利用できません。",community:"瞬間を共有",chat:"つながりを保つ",language:"言語を選択",lightMode:"ライトモード",darkMode:"ダークモード"},
  zh:{tagline:"发现你在意的人与精彩时刻。",loginTitle:"登录 SocialN",registerTitle:"创建 SocialN 帐户",email:"电子邮箱地址",password:"密码",name:"姓名",username:"用户名",login:"登录",register:"创建帐户",forgot:"忘记密码？",newAccount:"新建帐户",back:"已有帐户？登录",recovery:"密码找回功能暂不可用。",community:"分享精彩时刻",chat:"保持联系",language:"选择语言",lightMode:"浅色模式",darkMode:"深色模式"},
  th:{tagline:"ค้นพบผู้คนและช่วงเวลาที่คุณใส่ใจ",loginTitle:"เข้าสู่ระบบ SocialN",registerTitle:"สร้างบัญชี SocialN",email:"ที่อยู่อีเมล",password:"รหัสผ่าน",name:"ชื่อ-นามสกุล",username:"ชื่อผู้ใช้",login:"เข้าสู่ระบบ",register:"สร้างบัญชี",forgot:"ลืมรหัสผ่าน?",newAccount:"สร้างบัญชีใหม่",back:"มีบัญชีแล้ว? เข้าสู่ระบบ",recovery:"ยังไม่เปิดใช้การกู้คืนรหัสผ่าน",community:"แบ่งปันช่วงเวลา",chat:"เชื่อมต่อกันเสมอ",language:"เลือกภาษา",lightMode:"โหมดสว่าง",darkMode:"โหมดมืด"}
};
function Login({onLogin,language="en",onLanguageChange=()=>{},theme="dark",onThemeChange=()=>{}}){
  const params=new URLSearchParams(location.search),initialReset=params.get("reset_password")||"";
  const[mode,setMode]=useState(initialReset?"reset":"login"),[f,setF]=useState({email:"",username:"",name:"",password:"",code:"",confirm_password:""}),[err,setErr]=useState(""),[notice,setNotice]=useState(""),[busy,setBusy]=useState(false),[challenge,setChallenge]=useState("");
  const copy=AUTH_COPY[language]||AUTH_COPY.en;
  useEffect(()=>{const token=params.get("verify_email");if(!token)return;api("/api/auth/email/verify",{method:"POST",body:JSON.stringify({token})}).then(d=>{setNotice(d.message);history.replaceState({},"","/")}).catch(e=>setErr(e.message))},[]);
  function changeMode(next){setMode(next);setErr("");setNotice("")}
  async function sub(e){e.preventDefault();setBusy(true);setErr("");setNotice("");try{
    if(mode==="forgot"){const d=await api("/api/auth/forgot-password",{method:"POST",body:JSON.stringify({email:f.email})});setNotice(d.message);return}
    if(mode==="reset"){if(f.password!==f.confirm_password)throw Error("Password confirmation does not match");const d=await api("/api/auth/reset-password",{method:"POST",body:JSON.stringify({token:initialReset,new_password:f.password})});setNotice(d.message);history.replaceState({},"","/");setMode("login");return}
    if(mode==="2fa"){const d=await api("/api/auth/login/2fa",{method:"POST",body:JSON.stringify({challenge_token:challenge,code:f.code})});authService.saveToken(d.access_token);onLogin(d.user);return}
    const d=await api(`/api/auth/${mode}`,{method:"POST",body:JSON.stringify(f)});if(d.requires_2fa){setChallenge(d.challenge_token);setMode("2fa");return}authService.saveToken(d.access_token);onLogin(d.user)
  }catch(e){setErr(e.message)}finally{setBusy(false)}}
  return <div className="auth-shell social-auth-shell">
    <main className="social-auth-main">
      <section className="social-auth-intro">
        <div className="social-auth-brand" aria-label="SocialN">Social<span>N</span></div>
        <div className="social-auth-hero">
          <h1>{copy.tagline}</h1>
          <div className="social-auth-visual" aria-hidden="true">
            <div className="auth-scene-card auth-scene-main"><span className="auth-scene-avatar">S</span><div><b>SocialN</b><small>{copy.community}</small></div><i>♥</i></div>
            <div className="auth-scene-card auth-scene-photo"><span>☀</span><strong>Moments</strong></div>
            <div className="auth-scene-card auth-scene-chat"><span>☺</span><div><b>{copy.chat}</b><small>SocialN Messenger</small></div></div>
            <div className="auth-scene-reaction">♥</div>
          </div>
        </div>
      </section>
      <section className="social-auth-panel">
        <div className="auth-card social-auth-card">
          <div className="auth-mobile-brand">Social<span>N</span></div>
          <div className="social-auth-card-head">
            <h2>{mode==="login"?copy.loginTitle:mode==="register"?copy.registerTitle:mode==="2fa"?"Two-factor authentication":mode==="forgot"?"Reset your password":"Choose a new password"}</h2>
          </div>
          <form onSubmit={sub}>
            {mode==="register"&&<><input required autoComplete="name" placeholder={copy.name} value={f.name} onChange={e=>setF({...f,name:e.target.value})}/><input required autoComplete="username" placeholder={copy.username} value={f.username} onChange={e=>setF({...f,username:e.target.value})}/></>}
            {["login","register","forgot"].includes(mode)&&<input required type="email" autoComplete="email" placeholder={copy.email} value={f.email} onChange={e=>setF({...f,email:e.target.value})}/>}
            {["login","register","reset"].includes(mode)&&<input required minLength={8} type="password" autoComplete={mode==="login"?"current-password":"new-password"} placeholder={mode==="reset"?"New password":copy.password} value={f.password} onChange={e=>setF({...f,password:e.target.value})}/>}
            {mode==="reset"&&<input required minLength={8} type="password" autoComplete="new-password" placeholder="Confirm new password" value={f.confirm_password} onChange={e=>setF({...f,confirm_password:e.target.value})}/>}
            {mode==="2fa"&&<><p className="muted">Enter the 6-digit code from your authenticator app or a recovery code.</p><input required autoFocus inputMode="numeric" autoComplete="one-time-code" placeholder="Authentication code" value={f.code} onChange={e=>setF({...f,code:e.target.value})}/></>}
            {err&&<div className="error" role="alert">{err}</div>}
            {notice&&<div className="success-notice" role="status">{notice}</div>}
            <button className="primary wide auth-submit" disabled={busy}>{busy?"…":mode==="login"?copy.login:mode==="register"?copy.register:mode==="forgot"?"Send reset link":mode==="reset"?"Reset password":"Verify"}</button>
          </form>
          {mode==="login"&&<button type="button" className="auth-forgot" onClick={()=>changeMode("forgot")}>{copy.forgot}</button>}
          <div className="auth-divider"><span/></div>
          <button type="button" className="auth-create" onClick={()=>changeMode(mode==="login"?"register":"login")}>{mode==="login"?copy.newAccount:copy.back}</button>
        </div>
      </section>
    </main>
    <footer className="social-auth-languages" aria-label={copy.language}>
      {LANGUAGES.map(item=><button type="button" className={language===item.code?"active":""} key={item.code} onClick={()=>onLanguageChange(item.code)}>{item.label}</button>)}
      <span className="auth-footer-separator" aria-hidden="true"/>
      <button type="button" className="auth-theme-toggle" onClick={()=>onThemeChange(theme==="dark"?"light":"dark")} aria-label={theme==="dark"?copy.lightMode:copy.darkMode} title={theme==="dark"?copy.lightMode:copy.darkMode}>
        {theme==="dark"?<Sun size={18}/>:<Moon size={18}/>}<span>{theme==="dark"?copy.lightMode:copy.darkMode}</span>
      </button>
    </footer>
  </div>
}

const AUDIENCE_OPTIONS=[
  ["public","Public"],["friends","Friends"],["friends_except","Friends except…"],
  ["specific_friends","Specific friends"],["followers","Friends and followers"],
  ["custom","Custom audience"],["only_me","Only me"]
];
const emptyAudience=()=>({included_ids:[],excluded_ids:[],base:"friends"});
const defaultProfilePrivacy=()=>Object.fromEntries(["dob","hometown","relationship","albums","friends_list"].map(key=>[key,{audience:"friends",...emptyAudience()}]));
const audienceLabel=value=>AUDIENCE_OPTIONS.find(item=>item[0]===value)?.[1]||value;
function AudienceSelector({privacy,onPrivacyChange,audience=emptyAudience(),onAudienceChange=()=>{},compact=false}){
  const[friends,setFriends]=useState([]),[loading,setLoading]=useState(false);
  const advanced=["friends_except","specific_friends","custom"].includes(privacy);
  useEffect(()=>{if(!advanced||friends.length)return;setLoading(true);api("/api/friends").then(rows=>setFriends(Array.isArray(rows)?rows:[])).finally(()=>setLoading(false))},[advanced]);
  function setPerson(id,mode){const included=new Set(audience.included_ids||[]),excluded=new Set(audience.excluded_ids||[]);included.delete(id);excluded.delete(id);if(mode==="include")included.add(id);if(mode==="exclude")excluded.add(id);onAudienceChange({...audience,included_ids:[...included],excluded_ids:[...excluded]})}
  return <div className={`audience-selector ${compact?"compact":""}`}><select aria-label="Audience" value={privacy} onChange={e=>{onPrivacyChange(e.target.value);onAudienceChange(emptyAudience())}}>{AUDIENCE_OPTIONS.map(([value,label])=><option key={value} value={value}>{label}</option>)}</select>{advanced&&<div className="audience-popover"><b>{audienceLabel(privacy)}</b>{privacy==="custom"&&<label>Base audience<select value={audience.base||"friends"} onChange={e=>onAudienceChange({...audience,base:e.target.value})}><option value="friends">Friends</option><option value="followers">Friends and followers</option><option value="public">Public</option></select></label>}<div className="audience-people">{loading?<small>Loading friends…</small>:friends.map(person=>{const mode=(audience.included_ids||[]).includes(person.id)?"include":(audience.excluded_ids||[]).includes(person.id)?"exclude":"default";return <label key={person.id}><Avatar user={person} size={30}/><span>{person.name}</span>{privacy==="friends_except"?<input type="checkbox" checked={mode==="exclude"} onChange={e=>setPerson(person.id,e.target.checked?"exclude":"default")}/>:privacy==="specific_friends"?<input type="checkbox" checked={mode==="include"} onChange={e=>setPerson(person.id,e.target.checked?"include":"default")}/>:<select value={mode} onChange={e=>setPerson(person.id,e.target.value)}><option value="default">Use base</option><option value="include">Always include</option><option value="exclude">Exclude</option></select>}</label>})}{!loading&&!friends.length&&<small>No friends available for this audience.</small>}</div></div>}</div>
}

function PostComposer({onCreated}){
  const composerInputRef=useRef(null);
  const[content,setContent]=useState("");
  const[privacy,setPrivacy]=useState("public");
  const[audience,setAudience]=useState(emptyAudience);
  const[file,setFile]=useState(null);
  const[stickers,setStickers]=useState([]),[showStickers,setShowStickers]=useState(false);
  const[selectedGif,setSelectedGif]=useState(null),[showGifPicker,setShowGifPicker]=useState(false);
  const[gifQuery,setGifQuery]=useState(""),[gifResults,setGifResults]=useState([]),[gifLoading,setGifLoading]=useState(false),[gifError,setGifError]=useState("");
  const[busy,setBusy]=useState(false);
  const[error,setError]=useState("");

  useEffect(()=>{
    if(!showGifPicker)return;
    let cancelled=false;
    const timer=setTimeout(async()=>{
      setGifLoading(true);setGifError("");
      try{const result=await api(`/api/giphy?q=${encodeURIComponent(gifQuery.trim())}`);if(!cancelled)setGifResults(Array.isArray(result?.data)?result.data:[])}
      catch(e){if(!cancelled){setGifResults([]);setGifError(e.message)}}
      finally{if(!cancelled)setGifLoading(false)}
    },gifQuery.trim()?350:0);
    return()=>{cancelled=true;clearTimeout(timer)};
  },[showGifPicker,gifQuery]);

  function insertComposerSticker(item){
    const input=composerInputRef.current;
    const start=input?.selectionStart??content.length;
    const end=input?.selectionEnd??start;
    const next=`${content.slice(0,start)}${item}${content.slice(end)}`;
    const nextCaret=start+item.length;
    setSelectedGif(null);setContent(next);
    setTimeout(()=>{composerInputRef.current?.focus();composerInputRef.current?.setSelectionRange(nextCaret,nextCaret)},0);
  }

  async function submit(e){
    e.preventDefault();
    if(!content.trim()&&!file&&!stickers.length&&!selectedGif)return;
    setBusy(true);setError("");
    try{
      let image_url=null;
      if(file){
        const body=new FormData();body.append("file",file);
        image_url=(await api("/api/upload",{method:"POST",body})).url;
      }
      if(selectedGif)image_url=selectedGif.url;
      const post=await api("/api/posts",{method:"POST",body:JSON.stringify({content,privacy,audience,image_url,media_type:selectedGif?"gif":"image",sticker:stickers.length?JSON.stringify(stickers):null})});
      setContent("");setFile(null);setStickers([]);setShowStickers(false);setSelectedGif(null);setShowGifPicker(false);setGifQuery("");setAudience(emptyAudience());onCreated?.(post);
    }catch(e){setError(e.message)}finally{setBusy(false)}
  }

  return <form className="card composer" onSubmit={submit}>
    <div className="composer-title">Create post</div>
    <div className={`composer-row composer-rich-row ${stickers.length?"has-stickers":""}`}><textarea ref={composerInputRef} className={content?"has-text":""} value={content} onChange={e=>setContent(e.target.value)} onKeyDown={e=>{if(e.key==="Backspace"&&!content&&stickers.length){e.preventDefault();setStickers(current=>current.slice(0,-1))}}} placeholder={stickers.length?"":"What's on your mind?"}/>{stickers.length>0&&<div className="composer-sticker-previews">{stickers.map((item,index)=><span className="composer-sticker-preview" key={`${item}-${index}`}><i>{item}</i><button type="button" onClick={()=>setStickers(current=>current.filter((_,position)=>position!==index))} aria-label="Remove sticker"><X size={8}/></button></span>)}</div>}<span className="composer-rich-spacer"/></div>
    {file&&<div className="file-chip">{file.name}</div>}
    {selectedGif&&<div className="composer-gif-preview"><img src={selectedGif.preview_url} alt={selectedGif.title||"Selected GIF"}/><button type="button" onClick={()=>setSelectedGif(null)} aria-label="Remove GIF"><X size={17}/></button><span>GIF</span></div>}
    {error&&<div className="error">{error}</div>}
    <div className="composer-actions">
      <label className="action"><ImageIcon size={18}/> Photo<input hidden type="file" accept="image/*" onChange={e=>{setFile(e.target.files?.[0]||null);setSelectedGif(null)}}/></label>
      <div className="sticker-control"><button type="button" className={`action sticker-trigger ${showStickers?"active":""}`} onClick={()=>{setShowStickers(!showStickers);setShowGifPicker(false)}}><Smile size={19}/> Stickers</button>{showStickers&&<div className="sticker-library"><div className="sticker-library-head"><div><b>Stickers</b><small>Insert stickers like normal text</small></div><button type="button" className="icon-btn" onClick={()=>setShowStickers(false)}><X size={18}/></button></div><div className="sticker-grid">{STICKERS.map((item,index)=><button type="button" key={`${item}-${index}`} onClick={()=>insertComposerSticker(item)}>{item}</button>)}</div></div>}</div>
      <div className="composer-gif-control"><button type="button" className={`action composer-gif-trigger ${showGifPicker?"active":""}`} onClick={()=>{setShowGifPicker(!showGifPicker);setShowStickers(false)}}>GIF</button>{showGifPicker&&<div className="gif-picker composer-gif-picker"><div className="gif-picker-head"><b>Choose a GIF</b><button type="button" className="icon-btn" onClick={()=>setShowGifPicker(false)}><X size={18}/></button></div><input autoFocus value={gifQuery} onChange={e=>setGifQuery(e.target.value)} placeholder="Search GIPHY..."/><div className="gif-grid">{gifLoading&&<div className="gif-status">Loading GIFs...</div>}{gifError&&<div className="gif-status error">{gifError}</div>}{!gifLoading&&!gifError&&!gifResults.length&&<div className="gif-status">No GIFs found.</div>}{gifResults.map(item=><button type="button" key={item.id} title={item.title} onClick={()=>{setSelectedGif(item);setFile(null);setStickers([]);setShowGifPicker(false)}}><img src={item.preview_url} alt={item.title} loading="lazy"/></button>)}</div><div className="giphy-credit">Powered by GIPHY</div></div>}</div>
      <AudienceSelector privacy={privacy} onPrivacyChange={setPrivacy} audience={audience} onAudienceChange={setAudience} compact/>
      <button className="primary" disabled={busy||(!content.trim()&&!file&&!stickers.length&&!selectedGif)}>{busy?"Posting...":"Post"}</button>
    </div>
  </form>
}

function SharedPostPreview({shared,onOpenProfile,compact=false}){
  if(!shared||shared.available===false)return <div className={`shared-card shared-unavailable ${compact?"compact":""}`}><ShieldBan size={25}/><div><b>This content isn't available right now</b><small>The original post may have been deleted or its privacy has changed.</small></div></div>;
  const hasContent=Boolean(shared.content?.trim()),stickers=shared.sticker?messageStickers(shared.sticker):[];
  return <div className={`shared-card ${compact?"compact":""}`}><button type="button" className="shared-author" onClick={()=>onOpenProfile?.(shared.author.id)}><Avatar user={shared.author} size={34}/><span><b>{shared.author.name}</b><small>{formatDateTime(shared.created_at)}</small></span></button>{(hasContent||stickers.length>0)&&<div className={`post-rich-content ${hasContent?"mixed":"sticker-only"}`}>{hasContent&&<div className="shared-content">{shared.content}</div>}{stickers.length>0&&<div className="post-stickers shared-stickers" role="img" aria-label="Stickers">{stickers.map((item,index)=><span className="post-sticker" key={`${item}-${index}`}>{item}</span>)}</div>}</div>}{shared.image_url&&(shared.media_type==="video"?<video className="shared-image" src={asset(shared.image_url)} controls preload="metadata"/>:<img className="shared-image" src={asset(shared.image_url)} alt="Shared post"/>)}</div>
}

function ChatSharedPost({postId,onOpenProfile}){
  const[data,setData]=useState(null);
  useEffect(()=>{let live=true;setData(null);api(`/api/posts/${postId}`).then(row=>{if(live)setData({...row,available:true})}).catch(()=>{if(live)setData({id:postId,available:false})});return()=>{live=false}},[postId]);
  return data?<SharedPostPreview shared={data} onOpenProfile={onOpenProfile} compact/>:<div className="shared-card compact shared-loading">Loading shared post…</div>
}

function PostCard({post,me,onOpenProfile,onUpdated,onDeleted,onShared,onHidden}){
  const[comment,setComment]=useState("");
  const[editing,setEditing]=useState(false);
  const[menu,setMenu]=useState(false);
  const[draft,setDraft]=useState({content:post.content||"",privacy:post.privacy||"public",audience:post.audience||emptyAudience(),image_url:post.image_url||null,media_type:post.media_type||"image",sticker:post.sticker||null});
  const[busy,setBusy]=useState(false);
  const[reactionDialog,setReactionDialog]=useState(null);
  const[reactionFilter,setReactionFilter]=useState("all");
  const[shareDialog,setShareDialog]=useState(null);
  const[shareBusy,setShareBusy]=useState(false);
  const[shareNotice,setShareNotice]=useState("");
  const[saveDialog,setSaveDialog]=useState(null);

  async function react(type){try{const d=await api(`/api/posts/${post.id}/like`,{method:"POST",body:JSON.stringify({reaction:type})});onUpdated?.({...post,...d})}catch(e){alert(e.message)}}
  async function openReactions(){if(!(post.likes_count>0))return;setReactionFilter("all");setReactionDialog({loading:true,items:[]});try{const data=await api(`/api/posts/${post.id}/reactions`);setReactionDialog({loading:false,items:Array.isArray(data.items)?data.items:[]})}catch(e){setReactionDialog(null);alert(e.message)}}
  async function addComment(e){e.preventDefault();if(!comment.trim())return;try{const row=await api(`/api/posts/${post.id}/comments`,{method:"POST",body:JSON.stringify({content:comment})});setComment("");onUpdated?.({...post,comments:[...(post.comments||[]),row]})}catch(e){alert(e.message)}}
  async function saveEdit(){setBusy(true);try{const row=await api(`/api/posts/${post.id}`,{method:"PUT",body:JSON.stringify(draft)});setEditing(false);setMenu(false);onUpdated?.(row)}catch(e){alert(e.message)}finally{setBusy(false)}}
  async function remove(){if(!await confirmDialog({title:"Delete post?",message:"This post and its activity will be permanently removed.",detail:"This action cannot be undone.",confirmLabel:"Delete post"}))return;try{await api(`/api/posts/${post.id}`,{method:"DELETE"});onDeleted?.(post.id)}catch(e){alert(e.message)}}
  async function openShare(){setShareDialog({destination:"feed",caption:"",privacy:"public",audience:emptyAudience(),target_id:null,target_type:null,groups:[],conversations:[],loading:true});try{const[groups,conversationRows,friends]=await Promise.all([api("/api/groups"),api("/api/chat/conversations"),api("/api/friends")]),conversations=conversationRows||[],directIds=new Set(conversations.filter(item=>!item.is_group).map(item=>Number(item.user?.id)));for(const friend of friends||[])if(!directIds.has(Number(friend.id)))conversations.push({is_group:false,user:friend,last_message:""});setShareDialog(value=>value&&({...value,groups:(groups||[]).filter(item=>item.membership_status==="member"),conversations,loading:false}))}catch(e){setShareDialog(value=>value&&({...value,loading:false,error:e.message}))}}
  async function submitShare(e){e.preventDefault();if(!shareDialog||shareBusy)return;if(shareDialog.destination!=="feed"&&!shareDialog.target_id)return;setShareBusy(true);try{const data=await api(`/api/posts/${post.id}/share`,{method:"POST",body:JSON.stringify({destination:shareDialog.destination,caption:shareDialog.caption,privacy:shareDialog.privacy,audience:shareDialog.audience,target_id:shareDialog.target_id,target_type:shareDialog.target_type})});setShareDialog(null);setShareNotice(data.destination==="feed"?"Shared to your feed":data.destination==="group"?"Shared to the group":"Sent through Messenger");setTimeout(()=>setShareNotice(""),2800);onUpdated?.({...post,shares_count:data.shares_count??post.shares_count});if(data.share)onShared?.(data.share)}catch(e){setShareDialog(value=>value&&({...value,error:e.message}))}finally{setShareBusy(false)}}
  async function openPostAlbum(){await onOpenProfile?.(post.author.id);setTimeout(()=>document.getElementById(`profile-albums-${post.author.id}`)?.scrollIntoView({behavior:"smooth",block:"start"}),80)}
  async function hide(kind){try{await api(`/api/posts/${post.id}/${kind}`,{method:"POST"});setMenu(false);onHidden?.(post.id)}catch(e){alert(e.message)}}
  async function toggleFollow(){try{const following=!post.author_following;await api(`/api/users/${post.author.id}/follow`,{method:following?"POST":"DELETE"});setMenu(false);onUpdated?.({...post,author_following:following})}catch(e){alert(e.message)}}
  async function toggleFavorite(){try{const favorite=!post.author_favorite;await api(`/api/posts/authors/${post.author.id}/preference`,{method:"PUT",body:JSON.stringify({favorite})});setMenu(false);onUpdated?.({...post,author_favorite:favorite})}catch(e){alert(e.message)}}
  async function snooze(){try{await api(`/api/posts/authors/${post.author.id}/preference`,{method:"PUT",body:JSON.stringify({snooze_days:30})});setMenu(false);onHidden?.(post.id)}catch(e){alert(e.message)}}
  async function openSave(){setMenu(false);try{let rows=await api("/api/posts/collections");if(!rows.length){const created=await api("/api/posts/collections",{method:"POST",body:JSON.stringify({name:"Saved posts"})});rows=[created]}setSaveDialog({collections:rows,selected:rows[0]?.id,name:"",busy:false})}catch(e){alert(e.message)}}
  async function saveToCollection(e){e.preventDefault();if(!saveDialog?.selected)return;setSaveDialog({...saveDialog,busy:true});try{await api(`/api/posts/${post.id}/save`,{method:"POST",body:JSON.stringify({collection_id:Number(saveDialog.selected)})});onUpdated?.({...post,is_saved:true});setSaveDialog(null);setShareNotice("Saved to collection");setTimeout(()=>setShareNotice(""),2400)}catch(error){setSaveDialog({...saveDialog,busy:false,error:error.message})}}
  async function createCollection(){const name=saveDialog.name.trim();if(!name)return;try{const row=await api("/api/posts/collections",{method:"POST",body:JSON.stringify({name})});setSaveDialog({...saveDialog,collections:[...saveDialog.collections,row],selected:row.id,name:""})}catch(e){setSaveDialog({...saveDialog,error:e.message})}}
  async function unsave(){try{await api(`/api/posts/${post.id}/save`,{method:"DELETE"});setMenu(false);onUpdated?.({...post,is_saved:false})}catch(e){alert(e.message)}}
  const privacyLabel=audienceLabel(post.privacy);

  return <article className="card post" id={`post-${post.id}`}>
    <div className="post-head"><Avatar user={post.author} onClick={()=>onOpenProfile?.(post.author.id)}/><div className="post-author"><button className="name-link" onClick={()=>onOpenProfile?.(post.author.id)}><b>{post.author.name}</b></button><div className="privacy-line">{post.feed_reason&&<><span className="feed-reason">{post.feed_reason}</span> · </>}{privacyLabel} · {formatDateTime(post.created_at)}</div></div>
      <div className="post-menu-wrap"><button className="icon-btn" onClick={()=>setMenu(!menu)}><MoreHorizontal size={20}/></button>{menu&&<div className="post-menu smart-feed-menu">{post.is_owner?<><button onClick={()=>{setEditing(true);setMenu(false)}}><Edit2 size={16}/> Edit</button><button className="danger-link" onClick={remove}><Trash2 size={16}/> Delete</button></>:<><button onClick={()=>hide("hide")}><EyeOff size={16}/> Hide post</button><button onClick={()=>hide("show-fewer")}><UserMinus size={16}/> Show fewer like this</button><button onClick={toggleFollow}><Users size={16}/> {post.author_following?"Unfollow":"Follow"}</button><button onClick={toggleFavorite}><Star size={16}/> {post.author_favorite?"Remove from favorites":"Add to favorites"}</button><button onClick={snooze}><Clock3 size={16}/> Snooze for 30 days</button></>}<button onClick={post.is_saved?unsave:openSave}><Bookmark size={16}/> {post.is_saved?"Remove saved post":"Save to collection"}</button></div>}</div>
    </div>
    {editing?<div className="post-edit"><textarea value={draft.content} onChange={e=>setDraft({...draft,content:e.target.value})}/><AudienceSelector privacy={draft.privacy} onPrivacyChange={value=>setDraft({...draft,privacy:value})} audience={draft.audience} onAudienceChange={value=>setDraft({...draft,audience:value})}/><div className="edit-actions"><button className="secondary" onClick={()=>setEditing(false)}>Cancel</button><button className="primary" disabled={busy} onClick={saveEdit}>Save</button></div></div>:<>{(post.content?.trim()||post.sticker)&&<div className={`post-rich-content ${post.content?.trim()?"mixed":"sticker-only"}`}>{post.content?.trim()&&<div className="post-content">{post.content}</div>}{post.sticker&&<div className="post-stickers" role="img" aria-label="Stickers">{messageStickers(post.sticker).map((item,index)=><span className="post-sticker" key={`${item}-${index}`}>{item}</span>)}</div>}</div>}{post.album&&<button className="post-album-link" onClick={openPostAlbum}><ImageIcon size={15}/> {post.album.name}</button>}{post.image_url&&(post.media_type==="video"?<video className="post-image post-video" src={asset(post.image_url)} controls preload="metadata" playsInline/>:<img className={`post-image ${post.media_type==="gif"?"post-gif":""}`} src={asset(post.image_url)} alt={post.media_type==="gif"?"GIF":"Post"}/>)}</>}
    {post.shared_post&&<SharedPostPreview shared={post.shared_post} onOpenProfile={onOpenProfile}/>}
    <div className="post-stats"><button type="button" className="reaction-summary post-reaction-total" disabled={!post.likes_count} onClick={openReactions}>{Object.entries(post.reaction_counts||{}).filter(([,n])=>n>0).map(([key])=><span key={key}>{reactionInfo(key).emoji}</span>)} {post.likes_count||0} reactions</button><span>{post.comments?.length||0} comments · {post.shares_count||0} shares</span></div>
    <div className="post-buttons"><div className="reaction-wrap"><button className={post.my_reaction?"active":""} onClick={()=>react(post.my_reaction||"like")}><span>{post.my_reaction?reactionInfo(post.my_reaction).emoji:<ThumbsUp size={18}/>}</span> {post.my_reaction?reactionInfo(post.my_reaction).label:"Like"}</button><div className="reaction-picker">{REACTIONS.map(r=><button key={r.key} title={r.label} onClick={()=>react(r.key)}>{r.emoji}</button>)}</div></div><button onClick={()=>document.getElementById(`comment-${post.id}`)?.focus()}><MessageSquare size={18}/> Comment</button><button onClick={openShare}><Share2 size={18}/> Share</button></div>
    {shareNotice&&<div className="share-success"><Check size={17}/>{shareNotice}</div>}
    <div>{(post.comments||[]).map(c=><div className="comment" key={c.id}><Avatar user={c.author} size={32}/><div className="comment-body"><b>{c.author.name}</b><div>{c.content}</div></div></div>)}</div>
    <form className="comment-box" onSubmit={addComment}><input id={`comment-${post.id}`} value={comment} onChange={e=>setComment(e.target.value)} placeholder="Write a comment..."/><button><Send size={16}/></button></form>
    {reactionDialog&&<div className="modal-backdrop reaction-list-backdrop" onMouseDown={e=>{if(e.target===e.currentTarget)setReactionDialog(null)}}><section className="reaction-list-dialog" role="dialog" aria-modal="true" aria-label="People who reacted">
      <header><h3>Reactions</h3><button type="button" aria-label="Close" onClick={()=>setReactionDialog(null)}><X size={21}/></button></header>
      <nav className="reaction-list-tabs">
        <button type="button" className={reactionFilter==="all"?"active":""} onClick={()=>setReactionFilter("all")}>All <b>{reactionDialog.items.length}</b></button>
        {REACTIONS.filter(item=>(post.reaction_counts?.[item.key]||0)>0).map(item=><button type="button" className={reactionFilter===item.key?"active":""} key={item.key} title={item.label} onClick={()=>setReactionFilter(item.key)}><span>{item.emoji}</span><b>{post.reaction_counts[item.key]}</b></button>)}
      </nav>
      <div className="reaction-list-scroll">
        {reactionDialog.loading?<div className="reaction-list-status">Loading reactions…</div>:reactionDialog.items.filter(item=>reactionFilter==="all"||item.reaction===reactionFilter).map(item=><button type="button" className="reaction-person" key={item.user.id} onClick={()=>{setReactionDialog(null);onOpenProfile?.(item.user.id)}}><span className="reaction-person-avatar"><Avatar user={item.user} size={44}/><i>{reactionInfo(item.reaction).emoji}</i></span><span><b>{item.user.name}</b><small>@{item.user.username}</small></span><em>{reactionInfo(item.reaction).label}</em></button>)}
        {!reactionDialog.loading&&!reactionDialog.items.some(item=>reactionFilter==="all"||item.reaction===reactionFilter)&&<div className="reaction-list-status">No reactions yet.</div>}
      </div>
    </section></div>}
    {shareDialog&&<div className="modal-backdrop share-dialog-backdrop" onMouseDown={e=>{if(e.target===e.currentTarget)setShareDialog(null)}}><form className="share-dialog" onSubmit={submitShare}><header><div><h3>Share post</h3><small>The original post's privacy still applies.</small></div><button type="button" className="icon-btn" onClick={()=>setShareDialog(null)}><X/></button></header><nav>{[["feed","Your feed"],["group","Group"],["messenger","Messenger"]].map(([key,label])=><button type="button" key={key} className={shareDialog.destination===key?"active":""} onClick={()=>setShareDialog({...shareDialog,destination:key,target_id:null,target_type:null,error:""})}>{label}</button>)}</nav><textarea value={shareDialog.caption} onChange={e=>setShareDialog({...shareDialog,caption:e.target.value})} placeholder="Say something about this…"/><SharedPostPreview shared={post.shared_post||{...post,available:true}} onOpenProfile={onOpenProfile} compact/>{shareDialog.destination==="feed"&&<label className="share-privacy">Audience<AudienceSelector privacy={shareDialog.privacy} onPrivacyChange={value=>setShareDialog({...shareDialog,privacy:value})} audience={shareDialog.audience} onAudienceChange={value=>setShareDialog({...shareDialog,audience:value})}/></label>}{shareDialog.destination==="group"&&<div className="share-targets">{shareDialog.groups.map(item=><button type="button" key={item.id} className={Number(shareDialog.target_id)===Number(item.id)?"selected":""} onClick={()=>setShareDialog({...shareDialog,target_id:item.id})}><UsersRound/><span><b>{item.name}</b><small>{item.privacy} · {item.member_count} members</small></span><Check/></button>)}{!shareDialog.loading&&!shareDialog.groups.length&&<p>You have not joined any groups.</p>}</div>}{shareDialog.destination==="messenger"&&<div className="share-targets">{shareDialog.conversations.map(item=>{const group=Boolean(item.is_group),targetId=group?item.group_chat_id:item.user?.id,title=group?item.name:item.user?.name;if(!targetId)return null;return <button type="button" key={`${group?"g":"u"}-${targetId}`} className={Number(shareDialog.target_id)===Number(targetId)&&shareDialog.target_type===(group?"group":"direct")?"selected":""} onClick={()=>setShareDialog({...shareDialog,target_id:targetId,target_type:group?"group":"direct"})}><Avatar user={group?{name:item.name,avatar_url:item.avatar_url}:item.user}/><span><b>{title}</b><small>{group?"Group chat":`@${item.user.username}`}</small></span><Check/></button>})}</div>}{shareDialog.loading&&<p className="muted">Loading destinations…</p>}{shareDialog.error&&<div className="error">{shareDialog.error}</div>}<footer><button type="button" className="secondary" onClick={()=>setShareDialog(null)}>Cancel</button><button className="primary" disabled={shareBusy||(shareDialog.destination!=="feed"&&!shareDialog.target_id)}>{shareBusy?"Sharing…":"Share now"}</button></footer></form></div>}
    {saveDialog&&<div className="modal-backdrop" onMouseDown={e=>{if(e.target===e.currentTarget)setSaveDialog(null)}}><form className="save-collection-dialog" onSubmit={saveToCollection}><header><div><h3>Save post</h3><small>Choose a collection.</small></div><button type="button" className="icon-btn" onClick={()=>setSaveDialog(null)}><X/></button></header><div className="collection-options">{saveDialog.collections.map(row=><label key={row.id}><input type="radio" name="collection" checked={Number(saveDialog.selected)===Number(row.id)} onChange={()=>setSaveDialog({...saveDialog,selected:row.id})}/><span><b>{row.name}</b><small>{row.posts_count||0} posts</small></span></label>)}</div><div className="new-collection"><input value={saveDialog.name} onChange={e=>setSaveDialog({...saveDialog,name:e.target.value})} placeholder="New collection name"/><button type="button" className="secondary" onClick={createCollection}>Create</button></div>{saveDialog.error&&<div className="error">{saveDialog.error}</div>}<footer><button type="button" className="secondary" onClick={()=>setSaveDialog(null)}>Cancel</button><button className="primary" disabled={saveDialog.busy||!saveDialog.selected}>{saveDialog.busy?"Saving…":"Save"}</button></footer></form></div>}
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
  const[form,setForm]=useState({name:"",description:"",privacy:"friends",audience:emptyAudience()});
  const[editForm,setEditForm]=useState({name:"",description:"",privacy:"friends",audience:emptyAudience()});
  const mine=Number(user.id)===Number(me.id);
  async function load(){try{setAlbums(await api(`/api/albums/user/${user.id}`))}catch(e){console.error(e);setAlbums([])}}
  useEffect(()=>{load();setSelected(null)},[user.id,user.avatar_url,user.cover_url]);
  async function openAlbum(id){try{setSelecting(false);setSelectedMedia(new Set());setSelected(await api(`/api/albums/${id}`))}catch(e){alert(e.message)}}
  async function create(e){e.preventDefault();setBusy(true);try{const row=await api("/api/albums",{method:"POST",body:JSON.stringify(form)});setCreating(false);setForm({name:"",description:"",privacy:"friends",audience:emptyAudience()});await load();await openAlbum(row.id)}catch(e){alert(e.message)}finally{setBusy(false)}}
  function beginEdit(){setEditForm({name:selected.name,description:selected.description||"",privacy:selected.privacy,audience:selected.audience||emptyAudience()});setEditing(true)}
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
    {creating&&<div className="modal-backdrop" onClick={()=>setCreating(false)}><form className="album-create-modal" onSubmit={create} onClick={e=>e.stopPropagation()}><div className="album-modal-title"><h3>Create album</h3><button type="button" className="icon-btn" onClick={()=>setCreating(false)}><X/></button></div><label>Album name<input required maxLength="150" value={form.name} onChange={e=>setForm({...form,name:e.target.value})}/></label><label>Description / notes<textarea maxLength="2000" placeholder="Write something about this album..." value={form.description} onChange={e=>setForm({...form,description:e.target.value})}/></label><label>Privacy<AudienceSelector privacy={form.privacy} onPrivacyChange={value=>setForm({...form,privacy:value})} audience={form.audience} onAudienceChange={value=>setForm({...form,audience:value})}/></label><button className="primary" disabled={busy}>{busy?"Creating...":"Create album"}</button></form></div>}
    {selected&&<div className="modal-backdrop album-view-backdrop" onClick={()=>setSelected(null)}><div className="album-view-modal" onClick={e=>e.stopPropagation()}><div className="album-modal-title"><div><h3>{selected.name}</h3><p>{selected.description||"No description"}</p><small>{selected.media_count} items · {selected.privacy}</small></div><button className="icon-btn" onClick={()=>setSelected(null)}><X/></button></div><div className="album-toolbar">{selected.is_owner&&selected.kind==="custom"&&<><label className="primary album-upload-button"><ImageIcon size={17}/>{busy?"Uploading...":"Add photos/videos"}<input hidden multiple type="file" accept="image/*,video/*" disabled={busy} onChange={e=>{upload([...e.target.files]);e.target.value=""}}/></label><button className="secondary" disabled={busy} onClick={beginEdit}><Edit2 size={16}/> Edit album</button><button className="danger" disabled={busy} onClick={deleteAlbum}><Trash2 size={16}/> Delete album</button></>}{selected.is_owner&&selected.media.length>0&&<button className={selecting?"secondary active-select":"secondary"} onClick={()=>{setSelecting(!selecting);setSelectedMedia(new Set())}}>{selecting?"Cancel selection":"Select media"}</button>}{selecting&&selectedMedia.size>0&&<button className="danger" disabled={busy} onClick={deleteSelected}><Trash2 size={16}/> Delete ({selectedMedia.size})</button>}</div><div className="album-media-grid">{selected.media.length===0?<div className="empty">No photos or videos yet.</div>:selected.media.map(m=><button className={selectedMedia.has(m.id)?"selected":""} key={m.id} onClick={()=>selecting?toggleMedia(m.id):setPreview({type:m.type,url:asset(m.url),name:m.caption||selected.name})}>{m.type==="video"?<video src={asset(m.url)} muted preload="metadata"/>:<img src={asset(m.url)} alt={m.caption||selected.name}/>}<span>{selecting?(selectedMedia.has(m.id)?"✓":"○"):(m.type==="video"?"▶":"")}</span></button>)}</div></div></div>}
    {editing&&selected&&<div className="modal-backdrop album-edit-backdrop" onClick={()=>setEditing(false)}><form className="album-create-modal" onSubmit={saveAlbum} onClick={e=>e.stopPropagation()}><div className="album-modal-title"><h3>Edit album</h3><button type="button" className="icon-btn" onClick={()=>setEditing(false)}><X/></button></div><label>Album name<input required maxLength="150" value={editForm.name} onChange={e=>setEditForm({...editForm,name:e.target.value})}/></label><label>Description / notes<textarea maxLength="2000" placeholder="Write something about this album..." value={editForm.description} onChange={e=>setEditForm({...editForm,description:e.target.value})}/></label><label>Privacy<AudienceSelector privacy={editForm.privacy} onPrivacyChange={value=>setEditForm({...editForm,privacy:value})} audience={editForm.audience} onAudienceChange={value=>setEditForm({...editForm,audience:value})}/></label><button className="primary" disabled={busy}>{busy?"Saving...":"Save changes"}</button></form></div>}
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
    relationship_partner_id:user.relationship_partner_id||null,
    relationship_since:user.relationship_since||"",
    bio:user.bio||""
  });
  const [partnerQuery,setPartnerQuery]=useState("");
  const [partnerResults,setPartnerResults]=useState([]);
  const [selectedPartner,setSelectedPartner]=useState(user.relationship_partner||null);
  const [coverBusy,setCoverBusy]=useState(false);
  const [confirmUnfriend,setConfirmUnfriend]=useState(false);
  const [imageEditor,setImageEditor]=useState(null);
  const [photoMenu,setPhotoMenu]=useState(null);
  const [contentVersion,setContentVersion]=useState(0);
  const [profileActionMenu,setProfileActionMenu]=useState(false),[profileSearchOpen,setProfileSearchOpen]=useState(false),[profileSearch,setProfileSearch]=useState("");

  useEffect(()=>{
    setForm({
      name:user.name||"",
      dob:user.dob||"",
      hometown:user.hometown||"",
      gender:user.gender||"",
      relationship_status:user.relationship_status||"",
      relationship_partner_id:user.relationship_partner_id||null,
      relationship_since:user.relationship_since||"",
      bio:user.bio||""
    });
    setSelectedPartner(user.relationship_partner||null);setPartnerQuery("");setPartnerResults([]);
  },[user.id,user.name,user.dob,user.hometown,user.gender,user.relationship_status,user.relationship_partner_id,user.relationship_since,user.bio]);

  useEffect(()=>{
    if(!editing||!partnerQuery.trim()){setPartnerResults([]);return}
    let cancelled=false;const timer=setTimeout(async()=>{try{const rows=await api("/api/friends"),needle=partnerQuery.trim().toLowerCase();if(!cancelled)setPartnerResults((rows||[]).filter(item=>item.id!==me.id&&(item.name?.toLowerCase().includes(needle)||item.username?.toLowerCase().includes(needle))).slice(0,8))}catch{if(!cancelled)setPartnerResults([])}},200);
    return()=>{cancelled=true;clearTimeout(timer)};
  },[partnerQuery,editing,me.id]);

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
  async function toggleFollow(){
    try{await api(`/api/users/${user.id}/follow`,{method:data.is_following?"DELETE":"POST"});await reload(user.id)}catch(e){alert(e.message)}
  }

  async function confirmRemoveFriend(){
    try{
      await api(`/api/friends/${user.id}`,{method:"DELETE"});
      setConfirmUnfriend(false);
      await reload(user.id);
    }catch(e){alert(e.message)}
  }

  async function block(){
    setProfileActionMenu(false);
    if(!await confirmDialog({variant:"danger",title:`Block ${user.name}?`,message:`${user.name} will no longer be able to find your profile, message you or interact with your content.`,detail:"Blocking also removes the current friendship. You can unblock this person later in Settings.",confirmLabel:"Block",cancelLabel:"Cancel"}))return;
    try{await api(`/api/users/${user.id}/block`,{method:"POST"});location.assign("/settings")}
    catch(e){alert(e.message)}
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
                  <button className="secondary" onClick={toggleFollow}>{data.is_following?"Following":"Follow"} · {data.followers_count||0}</button>
                  <div className="profile-more-wrap"><button className="secondary profile-more-trigger" aria-label="More profile actions" aria-expanded={profileActionMenu} onClick={()=>setProfileActionMenu(v=>!v)}><MoreHorizontal size={21}/></button>{profileActionMenu&&<div className="profile-action-menu">
                    <button onClick={()=>{setProfileActionMenu(false);setProfileSearchOpen(true);setTimeout(()=>document.getElementById("profile-content-search")?.focus(),0)}}><Search size={17}/><span><b>Search profile</b><small>Find posts by this person</small></span></button>
                    {data.relationship==="friends"&&<button onClick={()=>{setProfileActionMenu(false);setConfirmUnfriend(true)}}><UserCheck size={17}/><span><b>Unfriend</b><small>Remove {user.name} from your friends</small></span></button>}
                    <button className="danger-menu-item" onClick={block}><ShieldBan size={17}/><span><b>Block</b><small>Stop contact and interaction</small></span></button>
                  </div>}</div>
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

            <label className="full-row">
              <span>Relationship status</span>
              <select value={form.relationship_status} onChange={e=>{const status=e.target.value,settable=RELATIONSHIP_WITH_PARTNER.has(status);setForm({...form,relationship_status:status,relationship_partner_id:settable?form.relationship_partner_id:null,relationship_since:settable?form.relationship_since:""});if(!settable){setSelectedPartner(null);setPartnerQuery("");setPartnerResults([])}}}>
                <option value="">Not specified</option>
                <option value="single">Single</option>
                <option value="in_a_relationship">In a relationship</option>
                <option value="engaged">Engaged</option>
                <option value="married">Married</option>
                <option value="civil_union">In a civil union</option>
                <option value="domestic_partnership">In a domestic partnership</option>
                <option value="open_relationship">In an open relationship</option>
                <option value="complicated">It's complicated</option>
                <option value="separated">Separated</option>
                <option value="divorced">Divorced</option>
                <option value="widowed">Widowed</option>
                <option value="prefer_not_to_say">Prefer not to say</option>
              </select>
            </label>

            {RELATIONSHIP_WITH_PARTNER.has(form.relationship_status)&&<div className="relationship-details full-row">
              <label><span>Partner (optional)</span>{selectedPartner?<div className="relationship-partner-chip"><Avatar user={selectedPartner} size={38}/><span><b>{selectedPartner.name}</b><small>@{selectedPartner.username}</small></span><button type="button" title="Remove partner" onClick={()=>{setSelectedPartner(null);setForm({...form,relationship_partner_id:null})}}><X size={17}/></button></div>:<div className="relationship-search"><input value={partnerQuery} onChange={e=>setPartnerQuery(e.target.value)} placeholder="Search for a person to tag..."/>{partnerResults.length>0&&<div className="relationship-results">{partnerResults.map(item=><button type="button" key={item.id} onClick={()=>{setSelectedPartner(item);setForm({...form,relationship_partner_id:item.id});setPartnerQuery("");setPartnerResults([])}}><Avatar user={item} size={36}/><span><b>{item.name}</b><small>@{item.username}</small></span></button>)}</div>}</div>}</label>
              <label><span>{relationshipDateLabel(form.relationship_status)}</span><input type="date" value={form.relationship_since} onChange={e=>setForm({...form,relationship_since:e.target.value})}/></label>
            </div>}

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
          {(mine||data.privacy_visibility?.hometown)&&<span>📍 {user.hometown||"Hometown not set"}</span>}
          {(mine||data.privacy_visibility?.dob)&&<span>🎂 {user.dob?new Intl.DateTimeFormat(undefined,{dateStyle:"medium",timeZone:"UTC"}).format(new Date(`${user.dob}T00:00:00Z`)):"Birthday not set"}</span>}
          <span>⚧ {formatGender(user.gender)}</span>
          {(mine||data.privacy_visibility?.relationship)&&(data.pending_relationship?<span className="profile-relationship relationship-pending">❤️ {formatRelationship(data.pending_relationship.relationship_status)} with <button onClick={()=>open(data.pending_relationship.partner.id)}>{data.pending_relationship.partner.name}</button>{data.pending_relationship.relationship_since&&<> · since {formatDate(data.pending_relationship.relationship_since)}</>} <b>(pending)</b></span>:<span className="profile-relationship">❤️ {formatRelationship(user.relationship_status)}{user.relationship_partner&&<> with <button onClick={()=>open(user.relationship_partner.id)}>{user.relationship_partner.name}</button></>}{user.relationship_since&&<> · since {formatDate(user.relationship_since)}</>}</span>)}
        </div>}

        {!mine&&data.mutual_friends?.length>0&&<div className="mutual-section">
          <h3>Mutual friends</h3>
          <div className="people-grid compact-grid">
            {data.mutual_friends.map(x=><button className="person person-button" key={x.id} onClick={()=>open(x.id)}><Avatar user={x} size={54}/><b>{x.name}</b><span className="muted">@{x.username}</span></button>)}
          </div>
        </div>}
      </div>
    </div>

    {(mine||data.privacy_visibility?.albums)&&<ProfileAlbums user={user} me={me} onProfileChanged={async()=>{setContentVersion(v=>v+1);await reload(user.id)}}/>}
    {profileSearchOpen&&<div className="card profile-content-search"><Search size={19}/><input id="profile-content-search" value={profileSearch} onChange={e=>setProfileSearch(e.target.value)} placeholder={`Search ${user.name}'s posts...`}/>{profileSearch&&<button onClick={()=>setProfileSearch("")} aria-label="Clear search"><X size={17}/></button>}<button className="secondary" onClick={()=>{setProfileSearchOpen(false);setProfileSearch("")}}>Close</button></div>}
    <ProfilePosts userId={user.id} me={me} open={open} query={profileSearchOpen?profileSearch:""} refreshKey={`${user.avatar_url||""}-${user.cover_url||""}-${contentVersion}`}/>

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
    civil_union:"In a civil union",
    domestic_partnership:"In a domestic partnership",
    open_relationship:"In an open relationship",
    complicated:"It's complicated",
    separated:"Separated",
    divorced:"Divorced",
    widowed:"Widowed",
    prefer_not_to_say:"Prefer not to say"
  };
  return map[value]||"Relationship status not set";
}

const RELATIONSHIP_WITH_PARTNER=new Set(["in_a_relationship","engaged","married","civil_union","domestic_partnership","open_relationship","complicated"]);
function relationshipDateLabel(status){return status==="engaged"?"Engagement date (optional)":status==="married"?"Wedding / anniversary date (optional)":"Start date (optional)"}

function ProfilePosts({userId,me,open,refreshKey,query=""}){
  const[posts,setPosts]=useState([]);

  async function load(){
    try{
      const rows=await api(`/api/posts/user/${userId}`);
      setPosts(Array.isArray(rows)?rows:[]);
    }catch(e){console.error(e);setPosts([])}
  }

  useEffect(()=>{load()},[userId,refreshKey]);

  if(posts.length===0)return <div className="card empty profile-posts-empty">No visible posts.</div>;
  const visible=query.trim()?posts.filter(post=>`${post.content||""} ${post.author?.name||""}`.toLowerCase().includes(query.trim().toLowerCase())):posts;
  if(query.trim()&&!visible.length)return <div className="card empty profile-posts-empty">No posts match “{query.trim()}”.</div>;

  return <div className="profile-posts">
    {visible.map(p=><PostCard key={p.id} post={p} me={me} onOpenProfile={open} onUpdated={updated=>setPosts(v=>v.map(x=>x.id===updated.id?updated:x))} onDeleted={id=>setPosts(v=>v.filter(x=>x.id!==id))} onHidden={id=>setPosts(v=>v.filter(x=>x.id!==id))} onShared={shared=>{if(Number(shared.author?.id)===Number(userId))setPosts(v=>[shared,...v])}}/>)}
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
  const displayUser=conversation.is_group?{name:conversation.name,avatar_url:conversation.avatar_url}:conversation.user;
  return <div className={`conversation-row ${active?"active":""} ${conversation.archived?"archived":""} ${personalStorage?"self-vault":""} ${conversation.unread_count>0&&!active?"has-unread":""}`}>
    <button className="conversation-main" onClick={onOpen}><Avatar user={displayUser}/><span>{displayUser.name}{personalStorage?" (You)":""}{conversation.is_group&&<small>{(conversation.members?.length||0)+(conversation.is_group_draft?1:0)} members{conversation.is_group_draft?" · Draft":""}</small>}{conversation.pinned&&!personalStorage&&<small className="pinned-label"><Pin size={11}/> Pinned</small>}<small>{conversation.last_message||({image:"Photo",video:"Video",voice:"Voice message",file:"File",sticker:"Sticker",gif:"GIF",post:"Shared post"}[conversation.last_message_type])||(personalStorage?"Personal storage":conversation.is_group?"Group chat":`@${conversation.user.username}`)}</small></span></button>
    {conversation.unread_count>0&&!active&&<span className="conversation-unread-count">{conversation.unread_count>99?"99+":conversation.unread_count}</span>}
    {!conversation.is_group_draft&&<div className="conversation-menu-wrap"><button className="conversation-more" onClick={()=>setMenu(!menu)} aria-label="Conversation actions"><MoreVertical size={18}/></button>{menu&&<div className="conversation-menu">
      {!personalStorage&&<button onClick={()=>action("pin")}><Pin size={15}/>{conversation.pinned?"Unpin":"Pin"}</button>}
      {!personalStorage&&<button onClick={()=>action("archive")}><Archive size={15}/>{conversation.archived?"Unarchive":"Archive"}</button>}
      <button className="danger-link" onClick={()=>action("delete")}><Trash2 size={15}/>Delete chat</button>
    </div>}</div>}
  </div>
}

function NewGroupChatModal({friends,onClose,onCreate}){
  const[name,setName]=useState(""),[query,setQuery]=useState(""),[selected,setSelected]=useState([]),[approval,setApproval]=useState(false);
  const visible=friends.filter(x=>`${x.name} ${x.username}`.toLowerCase().includes(query.toLowerCase()));
  function submit(e){e.preventDefault();if(!name.trim()||!selected.length)return;onCreate({is_group:true,is_group_draft:true,name:name.trim(),member_ids:selected,members:friends.filter(x=>selected.includes(x.id)),require_admin_approval:approval})}
  return <div className="modal-backdrop" onMouseDown={onClose}><form className="card new-chat-group" onMouseDown={e=>e.stopPropagation()} onSubmit={submit}><div className="section-head"><div><h2>Create a new group</h2><p>The group activates after the first message is sent.</p></div><button type="button" className="icon-btn" onClick={onClose}><X/></button></div><label>Group name<input autoFocus maxLength={120} value={name} onChange={e=>setName(e.target.value)} placeholder="Name your group"/></label><div className="group-chat-member-search"><Search size={18}/><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search friends..."/></div><div className="group-chat-picker">{visible.map(item=><label key={item.id}><input type="checkbox" checked={selected.includes(item.id)} onChange={()=>setSelected(v=>v.includes(item.id)?v.filter(id=>id!==item.id):[...v,item.id])}/><Avatar user={item}/><span><b>{item.name}</b><small>@{item.username}</small></span></label>)}</div><label className="group-chat-approval"><input type="checkbox" checked={approval} onChange={e=>setApproval(e.target.checked)}/> Require admin approval for members joining through invitations</label><div className="modal-actions"><button type="button" className="secondary" onClick={onClose}>Cancel</button><button className="primary" disabled={!name.trim()||!selected.length}>Create</button></div></form></div>
}

function GroupChatInfo({group,friends,onClose,onChanged,onApplied,onLeave}){
  const[details,setDetails]=useState(group),[busy,setBusy]=useState(false),[media,setMedia]=useState([]),[friendRows,setFriendRows]=useState(friends);
  const isAdmin=details.my_role==="admin",memberIds=new Set((details.members||[]).map(x=>Number(x.id))),available=friendRows.filter(x=>!memberIds.has(Number(x.id)));
  async function reload(){const d=await api(`/api/chat/group-conversations/${group.group_chat_id}/messages`);setDetails({...d.group,group_chat_id:d.group.id,is_group:true});setMedia(d.messages.filter(x=>x.attachment_url));onChanged?.()}
  async function save(){setBusy(true);try{const result=await api(`/api/chat/group-conversations/${group.group_chat_id}`,{method:"PUT",body:JSON.stringify({name:details.name,avatar_url:details.avatar_url||null,theme:details.theme||"default",quick_reaction:details.quick_reaction||"👍",require_admin_approval:Boolean(details.require_admin_approval),invite_enabled:Boolean(details.invite_enabled),member_customization:Boolean(details.member_customization)})});const updated={...group,...result.group,id:group.id,group_chat_id:group.group_chat_id,is_group:true};Object.assign(group,updated);setDetails(updated);onApplied?.(updated);onChanged?.();onClose()}catch(e){alert(e.message)}finally{setBusy(false)}}
  async function avatar(file){if(!file)return;const fd=new FormData();fd.append("file",file);try{const up=await api("/api/chat/upload",{method:"POST",body:fd});setDetails(v=>({...v,avatar_url:up.url}))}catch(e){alert(e.message)}}
  async function memberAction(member,action){try{if(action==="remove")await api(`/api/chat/group-conversations/${group.group_chat_id}/members/${member.id}`,{method:"DELETE"});else if(action==="add")await api(`/api/chat/group-conversations/${group.group_chat_id}/members/${member.id}`,{method:"POST"});else await api(`/api/chat/group-conversations/${group.group_chat_id}/members/${member.id}/role?role=${action}`,{method:"PUT"});await reload()}catch(e){alert(e.message)}}
  async function nickname(member){const value=window.prompt(`Nickname for ${member.name}`,member.nickname||"");if(value===null)return;try{await api(`/api/chat/group-conversations/${group.group_chat_id}/members/${member.id}/nickname?nickname=${encodeURIComponent(value)}`,{method:"PUT"});await reload()}catch(e){alert(e.message)}}
  async function preferences(minutes,sound=details.notification_sound||"default"){try{await api(`/api/chat/group-conversations/${group.group_chat_id}/preferences?mute_minutes=${minutes}&sound=${encodeURIComponent(sound)}`,{method:"PUT"});await reload()}catch(e){alert(e.message)}}
  async function reviewRequest(request,action){try{await api(`/api/chat/group-conversations/${group.group_chat_id}/join-requests/${request.id}/${action}`,{method:"POST"});await reload()}catch(e){alert(e.message)}}
  useEffect(()=>{reload().catch(()=>{});if(!friendRows.length)api("/api/friends").then(setFriendRows).catch(()=>{})},[]);
  const inviteUrl=details.invite_token?`${location.origin}/messages/invite/${details.invite_token}`:"";
  return <div className="modal-backdrop group-info-backdrop" onMouseDown={onClose}><aside className="group-chat-info" onMouseDown={e=>e.stopPropagation()}><div className="group-info-head"><b>Group settings</b><button onClick={onClose}><X/></button></div><div className="group-info-scroll"><section className="group-info-identity"><label><Avatar user={details} size={72}/>{isAdmin&&<><Camera size={17}/><input hidden type="file" accept="image/*" onChange={e=>avatar(e.target.files?.[0])}/></>}</label><input disabled={!isAdmin} value={details.name||""} onChange={e=>setDetails(v=>({...v,name:e.target.value}))}/></section><section><h3>Customize chat</h3><label>Theme<select disabled={!isAdmin&&!details.member_customization} value={details.theme||"default"} onChange={e=>setDetails(v=>({...v,theme:e.target.value}))}><option value="default">Default</option><option value="ocean">Ocean gradient</option><option value="sunset">Sunset gradient</option><option value="forest">Forest</option><option value="event">Celebration</option><option value="cinema">Cinema</option></select></label><label>Quick reaction<select disabled={!isAdmin&&!details.member_customization} value={details.quick_reaction||"👍"} onChange={e=>setDetails(v=>({...v,quick_reaction:e.target.value}))}>{["👍","❤️","😂","😮","😢","🔥","🎉"].map(x=><option key={x}>{x}</option>)}</select></label>{isAdmin&&<label className="toggle-row"><input type="checkbox" checked={Boolean(details.member_customization)} onChange={e=>setDetails(v=>({...v,member_customization:e.target.checked}))}/> Allow members to customize name, photo and theme</label>}{isAdmin&&<button className="primary" disabled={busy} onClick={save}>Save customization</button>}</section><section><h3>Members</h3>{details.members?.map(member=><div className="group-info-member" key={member.id}><Avatar user={member}/><span><b>{member.nickname||member.name}</b><small>{member.nickname?`${member.name} · `:""}{member.role}</small></span><button onClick={()=>nickname(member)}>Nickname</button>{isAdmin&&Number(member.id)!==Number(group.creator_id)&&<div><button onClick={()=>memberAction(member,member.role==="admin"?"member":"admin")}>{member.role==="admin"?"Remove admin":"Make admin"}</button><button className="danger-link" onClick={()=>memberAction(member,"remove")}>Remove</button></div>}</div>)}{isAdmin&&available.length>0&&<details><summary>Add members</summary>{available.map(member=><button className="group-info-add" key={member.id} onClick={()=>memberAction(member,"add")}><Avatar user={member}/>{member.name}<UserPlus size={17}/></button>)}</details>}</section><section><h3>Invitations & approval</h3>{isAdmin&&<><label className="toggle-row"><input type="checkbox" checked={Boolean(details.require_admin_approval)} onChange={e=>setDetails(v=>({...v,require_admin_approval:e.target.checked}))}/> Admin approval required</label><label className="toggle-row"><input type="checkbox" checked={Boolean(details.invite_enabled)} onChange={e=>setDetails(v=>({...v,invite_enabled:e.target.checked}))}/> Enable invitation link</label><button className="secondary" onClick={save}>Save invitation settings</button></>}{inviteUrl&&<button className="copy-invite" onClick={()=>navigator.clipboard.writeText(inviteUrl)}><Link2 size={17}/><span>{inviteUrl}</span><Copy size={16}/></button>}</section><section><h3>Notifications</h3><label>Mute<select value="" onChange={e=>preferences(Number(e.target.value))}><option value="">Choose duration</option><option value="15">15 minutes</option><option value="60">1 hour</option><option value="480">8 hours</option><option value="1440">24 hours</option><option value="-1">Until turned back on</option><option value="0">Turn notifications on</option></select></label><label><Volume2 size={16}/> Notification sound<select value={details.notification_sound||"default"} onChange={e=>preferences(details.muted_until?-1:0,e.target.value)}><option value="default">Default</option><option value="soft">Soft</option><option value="pop">Pop</option><option value="none">No sound</option></select></label></section><section><h3>Media & files</h3><div className="group-info-media">{media.map(item=><a key={item.id} href={asset(item.attachment_url)} target="_blank" rel="noreferrer">{item.message_type==="image"||item.message_type==="gif"?<img src={asset(item.attachment_url)}/>:<><FileText/><small>{item.attachment_name||item.message_type}</small></>}</a>)}{!media.length&&<p className="muted">No shared media or files.</p>}</div></section><section className="group-info-danger"><button className="danger" onClick={onLeave}>Leave group</button><button className="secondary">Report group</button></section></div></aside></div>
}

function DirectChatInfo({target,me,messages,onClose,onApplied,openProfile}){
  const[details,setDetails]=useState(null),[busy,setBusy]=useState(false),[query,setQuery]=useState(""),[effectPhrase,setEffectPhrase]=useState(""),[effectEmoji,setEffectEmoji]=useState("✨");
  useEffect(()=>{api(`/api/chat/${target.id}/settings`).then(setDetails).catch(e=>alert(e.message))},[target.id]);
  if(!details)return <div className="modal-backdrop group-info-backdrop" onMouseDown={onClose}><aside className="group-chat-info" onMouseDown={e=>e.stopPropagation()}><div className="group-info-head"><b>Conversation settings</b><button onClick={onClose}><X/></button></div><div className="empty">Loading...</div></aside></div>;
  const media=messages.filter(x=>x.attachment_url),matches=query.trim()?messages.filter(x=>(x.content||"").toLowerCase().includes(query.trim().toLowerCase())):[];
  async function save(){setBusy(true);try{const result=await api(`/api/chat/${target.id}/settings`,{method:"PUT",body:JSON.stringify({...details,mute_minutes:Number(details.mute_minutes||0)})});onApplied(result);onClose()}catch(e){alert(e.message)}finally{setBusy(false)}}
  function addEffect(){if(!effectPhrase.trim()||!effectEmoji.trim())return;setDetails(v=>({...v,word_effects:{...(v.word_effects||{}),[effectPhrase.trim()]:effectEmoji.trim()}}));setEffectPhrase("")}
  async function block(){if(!await confirmDialog({variant:"danger",title:`Block ${target.name}?`,message:"You will no longer be able to message each other.",confirmLabel:"Block"}))return;try{await api(`/api/users/${target.id}/block`,{method:"POST"});onClose()}catch(e){alert(e.message)}}
  return <div className="modal-backdrop group-info-backdrop" onMouseDown={onClose}><aside className="group-chat-info" onMouseDown={e=>e.stopPropagation()}><div className="group-info-head"><b>Conversation settings</b><button onClick={onClose}><X/></button></div><div className="group-info-scroll">
    <section className="group-info-identity"><Avatar user={target} size={72}/><b>{details.other_nickname||target.name}</b><small>@{target.username}</small></section>
    <section><h3>Customize chat</h3><label>Theme<select value={details.theme} onChange={e=>setDetails({...details,theme:e.target.value})}><option value="default">Default</option><option value="ocean">Ocean gradient</option><option value="sunset">Sunset gradient</option><option value="forest">Forest</option><option value="event">Celebration</option><option value="cinema">Cinema</option></select></label><label>Quick reaction<select value={details.quick_reaction} onChange={e=>setDetails({...details,quick_reaction:e.target.value})}>{["👍","❤️","😂","😮","😢","🔥","🎉"].map(x=><option key={x}>{x}</option>)}</select></label><label>Your nickname<input value={details.my_nickname||""} onChange={e=>setDetails({...details,my_nickname:e.target.value})}/></label><label>{target.name}'s nickname<input value={details.other_nickname||""} onChange={e=>setDetails({...details,other_nickname:e.target.value})}/></label></section>
    <section><h3>Word effects</h3><div className="word-effect-add"><input placeholder="Phrase" value={effectPhrase} onChange={e=>setEffectPhrase(e.target.value)}/><input className="emoji-input" value={effectEmoji} onChange={e=>setEffectEmoji(e.target.value)}/><button className="secondary" onClick={addEffect}>Add</button></div>{Object.entries(details.word_effects||{}).map(([phrase,emoji])=><div className="word-effect-row" key={phrase}><span>{phrase}</span><b>{emoji}</b><button onClick={()=>{const next={...details.word_effects};delete next[phrase];setDetails({...details,word_effects:next})}}><X size={15}/></button></div>)}</section>
    <section><h3>Privacy</h3><label>Disappearing messages<select value={details.disappearing_seconds||0} onChange={e=>setDetails({...details,disappearing_seconds:Number(e.target.value)})}><option value="0">Off</option><option value="10">10 seconds after read</option><option value="60">1 minute after read</option><option value="3600">1 hour after read</option><option value="86400">24 hours after read</option></select></label><label className="toggle-row"><input type="checkbox" checked={Boolean(details.restricted)} onChange={e=>setDetails({...details,restricted:e.target.checked})}/> Restrict this person</label></section>
    <section><h3>Notifications</h3><label>Mute<select value={details.mute_minutes??0} onChange={e=>setDetails({...details,mute_minutes:Number(e.target.value)})}><option value="0">Notifications on</option><option value="15">15 minutes</option><option value="60">1 hour</option><option value="480">8 hours</option><option value="1440">24 hours</option><option value="-1">Until turned back on</option></select></label></section>
    <section><h3>Search conversation</h3><input placeholder="Search messages..." value={query} onChange={e=>setQuery(e.target.value)}/>{matches.map(x=><div className="chat-search-result" key={x.id}>{x.content}</div>)}</section>
    <section><h3>Media & files</h3><div className="group-info-media">{media.map(item=><a key={item.id} href={asset(item.attachment_url)} target="_blank" rel="noreferrer">{["image","gif"].includes(item.message_type)?<img src={asset(item.attachment_url)}/>:<><FileText/><small>{item.attachment_name||item.message_type}</small></>}</a>)}{!media.length&&<p className="muted">No shared media or files.</p>}</div></section>
    <section><button className="secondary" onClick={()=>{onClose();openProfile(target.id)}}>View profile</button><button className="danger" onClick={block}>Block</button></section><button className="primary direct-settings-save" disabled={busy} onClick={save}>{busy?"Saving...":"Save settings"}</button>
  </div></aside></div>
}

function MediaPreview({media,onClose}){
  useEffect(()=>{const close=e=>{if(e.key==="Escape")onClose()};window.addEventListener("keydown",close);return()=>window.removeEventListener("keydown",close)},[onClose]);
  if(!media)return null;
  return <div className="media-preview-backdrop" onClick={onClose}><div className="media-preview-modal" onClick={e=>e.stopPropagation()}>
    <div className="media-preview-head"><span>{media.name||"Media preview"}</span><a href={media.url} download={media.name} title="Download"><Download size={19}/></a><button onClick={onClose} aria-label="Close preview"><X size={22}/></button></div>
    <div className="media-preview-body">{media.type==="video"?<video src={media.url} controls autoPlay playsInline/>:<img src={media.url} alt={media.name||"Image preview"}/>}</div>
  </div></div>
}

function Chat({me,target,open,onChanged,onGroupActivated,onGroupSettingsChanged,onMobileBack,friends=[]}){
  const [messages,setMessages]=useState([]);
  const [text,setText]=useState("");
  const [connected,setConnected]=useState(false);
  const [sending,setSending]=useState(false);
  const endRef=useRef(null);
  const composeInputRef=useRef(null);
  const wsRef=useRef(null);
  const retryRef=useRef(null);
  const pingRef=useRef(null);
  const recorderRef=useRef(null);
  const chunksRef=useRef([]);
  const typingStopRef=useRef(null);
  const typingHideRef=useRef(null);
  const[recording,setRecording]=useState(false);
  const[presence,setPresence]=useState({online:false,last_seen_at:null,active_status_visible:false});
  const[isOtherTyping,setIsOtherTyping]=useState(false);
  const[previewMedia,setPreviewMedia]=useState(null);
  const[selectedStickers,setSelectedStickers]=useState([]),[showStickers,setShowStickers]=useState(false);
  const[selectedGif,setSelectedGif]=useState(null),[showGifPicker,setShowGifPicker]=useState(false);
  const[gifQuery,setGifQuery]=useState(""),[gifResults,setGifResults]=useState([]),[gifLoading,setGifLoading]=useState(false),[gifError,setGifError]=useState("");
  const[replyingTo,setReplyingTo]=useState(null),[messageMenu,setMessageMenu]=useState(null);
  const[reactionMenu,setReactionMenu]=useState(null);
  const[forwarding,setForwarding]=useState(null),[forwardTargets,setForwardTargets]=useState([]),[actionBusy,setActionBusy]=useState(false);
  const[pollOpen,setPollOpen]=useState(false),[pollQuestion,setPollQuestion]=useState(""),[pollOptions,setPollOptions]=useState(["",""]);
  const[groupInfoOpen,setGroupInfoOpen]=useState(false);
  const[directInfoOpen,setDirectInfoOpen]=useState(false),[directSettings,setDirectSettings]=useState(null);
  const[settingsNotice,setSettingsNotice]=useState("");
  const[mentionIndex,setMentionIndex]=useState(0);

  function lastActiveLabel(value){
    if(!value)return "Offline";
    const seconds=Math.max(0,Math.floor((Date.now()-new Date(value.endsWith?.("Z")?value:`${value}Z`).getTime())/1000));
    if(seconds<60)return "Offline · Active just now";
    if(seconds<3600)return `Offline · Active ${Math.floor(seconds/60)} minute${seconds<120?"":"s"} ago`;
    if(seconds<86400)return `Offline · Active ${Math.floor(seconds/3600)} hour${seconds<7200?"":"s"} ago`;
    if(seconds<604800)return `Offline · Active ${Math.floor(seconds/86400)} day${seconds<172800?"":"s"} ago`;
    return `Offline · Active ${formatDate(value)}`;
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
      reply_to_id:x.reply_to_id==null?null:Number(x.reply_to_id),
      reply_to:x.reply_to||null,
      is_forwarded:Boolean(x.is_forwarded||x.forwarded_from_id),
      is_pinned:Boolean(x.is_pinned),
      is_unsent:Boolean(x.is_unsent),
      poll:x.poll||null,
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

  function scrollChatToEnd(behavior="smooth"){
    requestAnimationFrame(()=>endRef.current?.scrollIntoView?.({behavior,block:"end"}));
  }

  async function loadHistory(silent=false){
    if(!target?.id)return;
    try{
      const response=await api(target.is_group?`/api/chat/group-conversations/${target.group_chat_id}/messages`:`/api/chat/${target.id}/messages`);
      const rows=target.is_group?response.messages:response;
      if(Array.isArray(rows))mergeMessages(rows);
      onChanged?.();
    }catch(e){
      if(!silent)console.error("Cannot load chat history:",e);
    }
  }

  useEffect(()=>{
    setMessages([]);setSelectedStickers([]);setShowStickers(false);setSelectedGif(null);setShowGifPicker(false);setGifQuery("");setReplyingTo(null);setMessageMenu(null);setForwarding(null);setIsOtherTyping(false);setPresence({online:false,last_seen_at:null,active_status_visible:false});
    if(target?.id&&!target.is_group_draft)loadHistory();
    if(target?.id&&!target.is_group)api(`/api/chat/${target.id}/settings`).then(setDirectSettings).catch(()=>setDirectSettings(null));else setDirectSettings(null);
  },[target?.id,target?.group_chat_id]);

  useEffect(()=>{
    if(!showGifPicker)return;
    let cancelled=false;
    const timer=setTimeout(async()=>{
      setGifLoading(true);setGifError("");
      try{
        const result=await api(`/api/giphy?q=${encodeURIComponent(gifQuery.trim())}`);
        if(!cancelled)setGifResults(Array.isArray(result?.data)?result.data:[]);
      }catch(e){if(!cancelled){setGifResults([]);setGifError(e.message)}}
      finally{if(!cancelled)setGifLoading(false)}
    },gifQuery.trim()?350:0);
    return()=>{cancelled=true;clearTimeout(timer)};
  },[showGifPicker,gifQuery]);

  useEffect(()=>{
    if(!target?.id||target.is_group)return;
    let stopped=false;
    async function loadPresence(){try{const d=await api(`/api/chat/presence/${target.id}`);if(!stopped)setPresence(d)}catch(e){console.error(e)}}
    loadPresence();const timer=setInterval(loadPresence,10000);
    return()=>{stopped=true;clearInterval(timer)};
  },[target?.id,target?.is_group]);

  useEffect(()=>{
    scrollChatToEnd();
  },[messages.length,isOtherTyping]);

  // REST polling fallback: guarantees incoming messages even if WebSocket/proxy fails.
  useEffect(()=>{
    if(!target?.id||target.is_group_draft)return;
    const timer=setInterval(()=>loadHistory(true),2500);
    return()=>clearInterval(timer);
  },[target?.id,target?.group_chat_id]);

  useEffect(()=>{
    let stopped=false;

    function connect(){
      if(stopped||!tok())return;
      let socket;
      try{
        socket=createAuthenticatedSocket("/api/chat/ws");
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
          if(data?.type==="message_updated"){
            setMessages(prev=>prev.map(m=>m.id===Number(data.message_id)?{...m,...data,content:data.is_unsent?"":m.content,attachment_url:data.is_unsent?null:m.attachment_url,sticker:data.is_unsent?null:m.sticker,reaction_counts:data.is_unsent?{}:m.reaction_counts}:m));
            return;
          }
          if(data?.type==="poll_updated"&&data.message){mergeMessages(data.message);return}
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
          const belongs=target.is_group
            ? Number(data.group_chat_id)===Number(target.group_chat_id)
            : !data.group_chat_id&&(
              (x.from_user_id===currentId&&x.to_user_id===meId)||
              (x.from_user_id===meId&&x.to_user_id===currentId)||
              (x.sender_id===currentId)
            );

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
    if(!target||(!value&&!selectedStickers.length&&!selectedGif)||sending)return;

    setSending(true);
    setText("");
    const stickersToSend=[...selectedStickers];
    const gifToSend=selectedGif;
    setSelectedStickers([]);setShowStickers(false);setSelectedGif(null);setShowGifPicker(false);
    emitTyping(false);

    try{
      const messageData=gifToSend?{content:value,message_type:"gif",attachment_url:gifToSend.url,attachment_name:gifToSend.title||"GIPHY GIF",attachment_mime:"image/gif",reply_to_id:replyingTo?.id||null}:{content:value,message_type:stickersToSend.length?"sticker":"text",sticker:stickersToSend.length?JSON.stringify(stickersToSend):null,reply_to_id:replyingTo?.id||null};
      const result=await api(target.is_group_draft?"/api/chat/group-conversations":target.is_group?`/api/chat/group-conversations/${target.group_chat_id}/messages`:`/api/chat/${target.id}/messages`,{
        method:"POST",
        body:JSON.stringify(target.is_group_draft?{name:target.name,member_ids:target.member_ids,require_admin_approval:target.require_admin_approval,first_message:messageData}:messageData)
      });
      const sent=result.message||result;
      if(target.is_group_draft)onGroupActivated?.({...result.group,id:result.group.id,group_chat_id:result.group.id});
      setReplyingTo(null);
      mergeMessages(sent);
      if(!target.is_group_draft)await loadHistory(true);
      onChanged?.();
    }catch(e){
      console.error("Send message failed:",e);
      setText(value);
      setSelectedStickers(stickersToSend);
      setSelectedGif(gifToSend);
      alert(`Could not send message: ${e.message}`);
    }finally{
      setSending(false);
    }
  }

  function emitTyping(isTyping){
    if(target?.is_group)return;
    try{if(target?.id!==me.id&&wsRef.current?.readyState===WebSocket.OPEN)wsRef.current.send(JSON.stringify({type:"typing",to_user_id:target.id,is_typing:isTyping}))}catch{}
  }
  function changeText(value){
    setText(value);clearTimeout(typingStopRef.current);emitTyping(Boolean(value.trim()));
    if(value.trim())typingStopRef.current=setTimeout(()=>emitTyping(false),1200);
  }

  function insertChatSticker(item){
    const input=composeInputRef.current;
    const start=input?.selectionStart??text.length;
    const end=input?.selectionEnd??start;
    const next=`${text.slice(0,start)}${item}${text.slice(end)}`;
    const nextCaret=start+item.length;
    setSelectedGif(null);setSelectedStickers([]);changeText(next);
    setTimeout(()=>{composeInputRef.current?.focus();composeInputRef.current?.setSelectionRange(nextCaret,nextCaret)},0);
  }

  async function uploadAttachment(file,forcedType){
    if(!target||!file||sending)return;
    setSending(true);
    try{
      const fd=new FormData();fd.append("file",file);
      const uploaded=await api("/api/chat/upload",{method:"POST",body:fd});
      const messageData={content:"",message_type:forcedType||uploaded.message_type,attachment_url:uploaded.url,attachment_name:uploaded.name,attachment_mime:uploaded.mime,reply_to_id:replyingTo?.id||null};
      const result=await api(target.is_group_draft?"/api/chat/group-conversations":target.is_group?`/api/chat/group-conversations/${target.group_chat_id}/messages`:`/api/chat/${target.id}/messages`,{method:"POST",body:JSON.stringify(target.is_group_draft?{name:target.name,member_ids:target.member_ids,require_admin_approval:target.require_admin_approval,first_message:messageData}:messageData)});
      mergeMessages(result.message||result);if(target.is_group_draft)onGroupActivated?.({...result.group,id:result.group.id,group_chat_id:result.group.id});setReplyingTo(null);onChanged?.();
    }catch(e){alert(`Could not send attachment: ${e.message}`)}finally{setSending(false)}
  }

  async function reactMessage(messageId,reaction){
    try{
      const d=await api(`/api/chat/messages/${messageId}/reaction`,{method:"POST",body:JSON.stringify({reaction})});
      setMessages(prev=>prev.map(m=>m.id===messageId?{...m,reaction_counts:d.reaction_counts||{},my_reaction:d.my_reaction}:m));
      setReactionMenu(null);
    }catch(e){alert(e.message)}
  }

  function toggleMessageReactions(messageId,event){
    if(reactionMenu?.id===messageId){setReactionMenu(null);return}
    const rect=event.currentTarget.getBoundingClientRect();
    const width=Math.min(276,window.innerWidth-20);
    const left=Math.max(10,Math.min(rect.left+rect.width/2-width/2,window.innerWidth-width-10));
    const top=rect.top>=66?rect.top-58:Math.min(rect.bottom+8,window.innerHeight-60);
    setReactionMenu({id:messageId,left,top,width});
  }

  function messageSummary(message){
    if(!message)return "Message";
    if(message.is_unsent)return "Message was unsent";
    if(message.content)return message.content;
    return {image:"Photo",video:"Video",voice:"Voice message",file:message.attachment_name||"File",sticker:"Sticker",gif:"GIF",post:"Shared post"}[message.message_type]||"Message";
  }

  async function toggleMessagePin(message){
    setActionBusy(true);
    try{const d=await api(`/api/chat/messages/${message.id}/pin`,{method:"POST"});setMessages(prev=>prev.map(m=>m.id===message.id?{...m,is_pinned:d.is_pinned}:m));setMessageMenu(null)}
    catch(e){alert(e.message)}finally{setActionBusy(false)}
  }

  async function unsendMessage(message){
    if(!await confirmDialog({variant:"danger",title:"Unsend message?",message:"This message will be removed for everyone in the conversation.",confirmLabel:"Unsend",cancelLabel:"Cancel"}))return;
    setActionBusy(true);
    try{await api(`/api/chat/messages/${message.id}`,{method:"DELETE"});setMessages(prev=>prev.map(m=>m.id===message.id?{...m,is_unsent:true,is_pinned:false,content:"",attachment_url:null,sticker:null,reaction_counts:{}}:m));setMessageMenu(null)}
    catch(e){alert(e.message)}finally{setActionBusy(false)}
  }

  async function openForward(message){
    setMessageMenu(null);setForwarding(message);
    try{const rows=await api("/api/chat/conversations");setForwardTargets((Array.isArray(rows)?rows:[]).filter(item=>item?.user?.id))}catch(e){alert(e.message);setForwarding(null)}
  }

  async function forwardTo(user){
    setActionBusy(true);
    try{await api(`/api/chat/messages/${forwarding.id}/forward/${user.id}`,{method:"POST"});setForwarding(null);onChanged?.()}
    catch(e){alert(e.message)}finally{setActionBusy(false)}
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

  async function createPoll(){
    if(!target?.is_group||target.is_group_draft||!pollQuestion.trim()||pollOptions.filter(x=>x.trim()).length<2)return;
    try{const result=await api(`/api/chat/group-conversations/${target.group_chat_id}/polls`,{method:"POST",body:JSON.stringify({question:pollQuestion,options:pollOptions})});mergeMessages(result);setPollOpen(false);setPollQuestion("");setPollOptions(["",""])}catch(e){alert(e.message)}
  }
  async function votePoll(pollId,optionId){try{const result=await api(`/api/chat/polls/${pollId}/vote/${optionId}`,{method:"POST"});mergeMessages(result)}catch(e){alert(e.message)}}
  async function sendQuickReaction(){try{const endpoint=target.is_group?`/api/chat/group-conversations/${target.group_chat_id}/messages`:`/api/chat/${target.id}/messages`,reaction=(target.is_group?target.quick_reaction:directSettings?.quick_reaction)||"👍";const result=await api(endpoint,{method:"POST",body:JSON.stringify({content:"",message_type:"sticker",sticker:JSON.stringify([reaction])})});mergeMessages(result);onChanged?.()}catch(e){alert(e.message)}}

  const mentionMatch=target?.is_group?text.match(/(^|\s)@([^\s@]*)$/):null;
  const mentionQuery=(mentionMatch?.[2]||"").toLowerCase();
  const mentionCandidates=mentionMatch?[{id:"all",name:"Everyone",username:"all",nickname:"Notify all group members"},...(target.members||[]).filter(member=>Number(member.id)!==Number(me.id))].filter(member=>`${member.name||""} ${member.username||""} ${member.nickname||""}`.toLowerCase().includes(mentionQuery)).slice(0,8):[];
  function insertMention(member){
    if(!mentionMatch)return;
    const start=text.length-mentionMatch[0].length+mentionMatch[1].length;
    const value=`${text.slice(0,start)}@${member.username} `;
    changeText(value);setMentionIndex(0);setTimeout(()=>composeInputRef.current?.focus(),0);
  }

  if(!target)return <div className="card empty chat-empty">Choose someone to message.</div>;

  return <div className={`chat card chat-theme-${target.is_group?(target.theme||"default"):(directSettings?.theme||"default")}`}>
    {settingsNotice&&<div className="chat-settings-notice"><Check size={17}/>{settingsNotice}</div>}
    <div className="chat-head profile-button" onClick={()=>!target.is_group&&open(target.id)}>
      <button type="button" className="chat-mobile-back" aria-label="Back to conversations" onClick={event=>{event.stopPropagation();onMobileBack?.()}}>←</button>
      <Avatar user={target}/>
      <div className="chat-head-copy">
        <b>{target.is_group?target.name:(directSettings?.other_nickname||target.name)}</b>
        {target.is_group?<div className="small muted">{(target.members?.length||0)+(target.is_group_draft?1:0)} members{target.is_group_draft?" · Draft":""}</div>:presence.active_status_visible===true&&<div className={`presence-line small ${presence.online?"online":"offline"}`}><span className="presence-dot"/>{presence.online?"Online":lastActiveLabel(presence.last_seen_at)}</div>}
      </div>
      {target.is_group&&!target.is_group_draft&&<button className="group-chat-info-trigger" title="Group information and settings" onClick={e=>{e.stopPropagation();setGroupInfoOpen(true)}}><Info size={21}/></button>}
      {!target.is_group&&<button className="group-chat-info-trigger" title="Conversation information and settings" onClick={e=>{e.stopPropagation();setDirectInfoOpen(true)}}><Info size={21}/></button>}
    </div>

    <div className="messages" onScroll={()=>setReactionMenu(null)}>
      {messages.map(x=><div key={x.id} className={`bubble ${x.sender_id===Number(me.id)?"mine":""} attachment-bubble ${x.message_type==="text"&&isEmojiOnlyMessage(x.content)?"emoji-only-bubble":""}`}>
        {target.is_group&&x.sender_id!==Number(me.id)&&<div className="group-message-sender">{target.members?.find(member=>Number(member.id)===Number(x.sender_id))?.name||"Group member"}</div>}
        {x.is_pinned&&<div className="message-pinned"><Pin size={12}/> Pinned</div>}
        {x.is_forwarded&&<div className="message-forwarded"><Share2 size={12}/> Forwarded</div>}
        {x.reply_to&&<button className="message-reply-preview" onClick={()=>document.getElementById(`message-${x.reply_to.id}`)?.scrollIntoView({behavior:"smooth",block:"center"})}><b>{Number(x.reply_to.sender_id)===Number(me.id)?"You":target.name}</b><span>{messageSummary(x.reply_to)}</span></button>}
        <span id={`message-${x.id}`} className="message-anchor"/>
        {x.message_type==="image"&&x.attachment_url&&<button className="chat-media-button" onClick={()=>setPreviewMedia({type:"image",url:asset(x.attachment_url),name:x.attachment_name})}><img className="chat-image" src={asset(x.attachment_url)} alt={x.attachment_name||"Image"} onLoad={()=>scrollChatToEnd("auto")}/><span className="media-hover-icon"><Maximize2 size={20}/></span></button>}
        {x.message_type==="video"&&x.attachment_url&&<div className="chat-video-wrap"><video className="chat-video" src={asset(x.attachment_url)} controls preload="metadata" playsInline/><button className="media-expand" onClick={()=>setPreviewMedia({type:"video",url:asset(x.attachment_url),name:x.attachment_name})}><Maximize2 size={16}/> Preview</button></div>}
        {x.message_type==="voice"&&x.attachment_url&&<audio className="chat-audio" controls src={asset(x.attachment_url)}/>}
        {x.message_type==="file"&&x.attachment_url&&<a className="chat-file" href={asset(x.attachment_url)} download={x.attachment_name}><FileText size={22}/><span>{x.attachment_name||"Download file"}</span><Download size={17}/></a>}
        {x.message_type==="gif"&&x.attachment_url&&<button className="chat-media-button chat-gif-button" onClick={()=>setPreviewMedia({type:"image",url:asset(x.attachment_url),name:x.attachment_name})}><img className="chat-gif" src={asset(x.attachment_url)} alt={x.attachment_name||"GIF"} onLoad={()=>scrollChatToEnd("auto")}/><span className="gif-label">GIF</span></button>}
        {x.message_type==="poll"&&x.poll&&<div className="chat-poll"><b>{x.poll.question}</b>{x.poll.options.map(option=><button key={option.id} onClick={()=>votePoll(x.poll.id,option.id)}><span>{option.label}</span><small>{option.votes} vote{option.votes===1?"":"s"}</small></button>)}</div>}
        {x.message_type==="post"&&x.attachment_name&&<ChatSharedPost postId={x.attachment_name} onOpenProfile={open}/>}
        {x.is_unsent?<div className="message-unsent">This message was unsent</div>:x.message_type==="sticker"?<div className={`message-with-sticker ${x.content&&x.sticker?"mixed":"sticker-only"}`}>{x.content&&x.sticker&&<span className="message-text">{x.content}</span>}<span className="message-stickers" role="img" aria-label="Stickers">{(x.stickers.length?x.stickers:messageStickers(x.sticker||x.content)).map((item,index)=><span className="message-sticker" key={`${item}-${index}`}>{item}</span>)}</span></div>:x.content&&<div className={x.message_type==="gif"?"gif-caption":undefined}>{x.content}</div>}
        {!target.is_group&&x.content&&Object.entries(directSettings?.word_effects||{}).filter(([phrase])=>x.content.toLowerCase().includes(phrase.toLowerCase())).map(([phrase,emoji])=><span className="word-effect-burst" key={phrase}>{emoji}</span>)}
        {!x.is_unsent&&<div className="message-actions"><div className="message-reaction-control"><button className="message-react-trigger" title="React" aria-expanded={reactionMenu?.id===x.id} onClick={event=>toggleMessageReactions(x.id,event)}>{x.my_reaction?reactionInfo(x.my_reaction).emoji:"☺"}</button><div className={`message-reaction-picker ${reactionMenu?.id===x.id?"is-open":""}`} style={reactionMenu?.id===x.id?{left:reactionMenu.left,top:reactionMenu.top,width:reactionMenu.width}:undefined}>{REACTIONS.map(r=><button key={r.key} title={r.label} onClick={()=>reactMessage(x.id,r.key)}>{r.emoji}</button>)}</div></div><button className="message-action-button" title="Reply" onClick={()=>{setReplyingTo(x);setMessageMenu(null);setReactionMenu(null);composeInputRef.current?.focus()}}><Reply size={15}/></button><div className="message-more-wrap"><button className="message-action-button" title="More" onClick={()=>{setReactionMenu(null);setMessageMenu(messageMenu===x.id?null:x.id)}}><MoreVertical size={16}/></button>{messageMenu===x.id&&<div className="message-action-menu">{x.sender_id===Number(me.id)&&<button disabled={actionBusy} onClick={()=>unsendMessage(x)}><Trash2 size={15}/> Unsend</button>}<button disabled={actionBusy} onClick={()=>openForward(x)}><Share2 size={15}/> Forward</button><button disabled={actionBusy} onClick={()=>toggleMessagePin(x)}><Pin size={15}/> {x.is_pinned?"Unpin":"Pin"}</button></div>}</div></div>}
        {Object.keys(x.reaction_counts||{}).length>0&&<div className="message-reaction-summary">{Object.entries(x.reaction_counts).filter(([,n])=>n>0).map(([key,n])=><span key={key}>{reactionInfo(key).emoji}{n>1?n:""}</span>)}</div>}
      </div>)}
      {isOtherTyping&&<div className="typing-indicator"><span/><span/><span/><b>{target.name} is typing...</b></div>}
      <div ref={endRef}/>
    </div>

    {replyingTo&&<div className="chat-replying"><Reply size={17}/><div><b>Replying to {replyingTo.sender_id===Number(me.id)?"yourself":target.name}</b><span>{messageSummary(replyingTo)}</span></div><button title="Cancel reply" onClick={()=>setReplyingTo(null)}><X size={18}/></button></div>}
    {pollOpen&&<div className="chat-poll-composer"><div><b>Create poll</b><button onClick={()=>setPollOpen(false)}><X size={17}/></button></div><input value={pollQuestion} onChange={e=>setPollQuestion(e.target.value)} placeholder="Ask a question"/>{pollOptions.map((value,index)=><input key={index} value={value} onChange={e=>setPollOptions(items=>items.map((item,i)=>i===index?e.target.value:item))} placeholder={`Option ${index+1}`}/>)}<div><button className="secondary" onClick={()=>setPollOptions(items=>[...items,""])}>Add option</button><button className="primary" onClick={createPoll}>Create poll</button></div></div>}
    {mentionCandidates.length>0&&<div className="mention-picker"><div className="mention-picker-title">Mention someone</div>{mentionCandidates.map((member,index)=><button type="button" key={member.id} className={index===mentionIndex?"active":""} onMouseDown={e=>{e.preventDefault();insertMention(member)}}>{member.id==="all"?<span className="mention-all">@</span>:<Avatar user={member} size={34}/>}<span><b>{member.nickname||member.name}</b><small>{member.id==="all"?"Notify everyone in this group":`@${member.username}`}</small></span></button>)}</div>}
    <div className="chat-input">
      <div className="chat-tools-strip" aria-label="Message attachments and tools">
      <label className="chat-tool" title="Send image or video"><ImageIcon size={19}/><input hidden type="file" accept="image/*,video/*" onChange={e=>{const f=e.target.files?.[0];uploadAttachment(f,f?.type.startsWith("video/")?"video":"image");e.target.value=""}}/></label>
      <label className="chat-tool" title="Send file"><Paperclip size={19}/><input hidden type="file" onChange={e=>{uploadAttachment(e.target.files?.[0],"file");e.target.value=""}}/></label>
      <button type="button" className={`chat-tool ${recording?"recording":""}`} title={recording?"Stop recording":"Record voice"} onClick={toggleRecording}>{recording?<Square size={17}/>:<Mic size={19}/>}</button>
      <div className="chat-sticker-control"><button type="button" className={`chat-tool ${showStickers?"active":""}`} title="Stickers" onClick={()=>{setShowStickers(!showStickers);setShowGifPicker(false)}}><Smile size={20}/></button>{showStickers&&<div className="sticker-library chat-sticker-library"><div className="sticker-library-head"><div><b>Stickers</b><small>Insert stickers like normal text</small></div><button type="button" className="icon-btn" onClick={()=>setShowStickers(false)}><X size={18}/></button></div><div className="sticker-grid">{STICKERS.map((item,index)=><button type="button" key={`chat-${item}-${index}`} onClick={()=>insertChatSticker(item)}>{item}</button>)}</div></div>}</div>
      <div className="chat-gif-control"><button type="button" className={`chat-tool gif-tool ${showGifPicker?"active":""}`} title="Send a GIF" onClick={()=>{setShowGifPicker(!showGifPicker);setShowStickers(false)}}>GIF</button>{showGifPicker&&<div className="gif-picker"><div className="gif-picker-head"><b>Choose a GIF</b><button type="button" className="icon-btn" onClick={()=>setShowGifPicker(false)}><X size={18}/></button></div><input autoFocus value={gifQuery} onChange={e=>setGifQuery(e.target.value)} placeholder="Search GIPHY..."/><div className="gif-grid">{gifLoading&&<div className="gif-status">Loading GIFs...</div>}{gifError&&<div className="gif-status error">{gifError}</div>}{!gifLoading&&!gifError&&!gifResults.length&&<div className="gif-status">No GIFs found.</div>}{gifResults.map(item=><button type="button" key={item.id} title={item.title} onClick={()=>{setSelectedGif(item);setSelectedStickers([]);setShowGifPicker(false);setTimeout(()=>composeInputRef.current?.focus(),0)}}><img src={item.preview_url} alt={item.title} loading="lazy"/></button>)}</div><div className="giphy-credit">Powered by GIPHY</div></div>}</div>
      {target.is_group&&!target.is_group_draft&&<button type="button" className="chat-tool poll-tool" title="Create poll" onClick={()=>setPollOpen(v=>!v)}>Poll</button>}
      </div>
      <div className={`chat-compose-field ${selectedStickers.length||selectedGif?"has-sticker":""}`}>
        <input
          ref={composeInputRef}
          className={text?"has-text":""}
          style={text?{width:`${Math.min(42,Math.max(3,text.length+1))}ch`}:undefined}
          value={text}
          placeholder={`Message ${target.name}...`}
          onChange={e=>changeText(e.target.value)}
          onKeyDown={e=>{
            if(mentionCandidates.length&&(e.key==="ArrowDown"||e.key==="ArrowUp")){e.preventDefault();setMentionIndex(index=>(index+(e.key==="ArrowDown"?1:-1)+mentionCandidates.length)%mentionCandidates.length);return}
            if(mentionCandidates.length&&(e.key==="Enter"||e.key==="Tab")){e.preventDefault();insertMention(mentionCandidates[Math.min(mentionIndex,mentionCandidates.length-1)]);return}
            if(mentionCandidates.length&&e.key==="Escape"){e.preventDefault();changeText(`${text} `);return}
            if(e.key==="Enter"&&!e.shiftKey){
              e.preventDefault();
              send();
            }
          }}
        />
        {selectedStickers.length>0&&<div className="chat-sticker-previews" title="Selected stickers">{selectedStickers.map((item,index)=><span className="chat-sticker-preview" key={`${item}-${index}`}><i>{item}</i><button type="button" onClick={()=>setSelectedStickers(current=>current.filter((_,position)=>position!==index))} aria-label="Remove sticker"><X size={10}/></button></span>)}</div>}
        {selectedGif&&<div className="selected-gif" title={selectedGif.title}><img src={selectedGif.preview_url} alt={selectedGif.title||"Selected GIF"}/><button type="button" onClick={()=>setSelectedGif(null)} aria-label="Remove GIF"><X size={12}/></button><span>GIF</span></div>}
        <span className="chat-compose-spacer"/>
      </div>
      <button type="button" className="primary" disabled={sending||(!text.trim()&&!selectedStickers.length&&!selectedGif)} onClick={send}>
        <Send size={18}/>
      </button>
      {!text.trim()&&!selectedGif&&!selectedStickers.length&&<button type="button" className="chat-quick-reaction" title="Quick reaction" onClick={sendQuickReaction}>{(target.is_group?target.quick_reaction:directSettings?.quick_reaction)||"👍"}</button>}
    </div>
    {forwarding&&<div className="forward-overlay" onMouseDown={e=>{if(e.target===e.currentTarget)setForwarding(null)}}><div className="forward-dialog card"><div className="forward-head"><div><b>Forward message</b><small>{messageSummary(forwarding)}</small></div><button onClick={()=>setForwarding(null)}><X size={19}/></button></div><div className="forward-list">{forwardTargets.length===0?<div className="empty compact">No conversations available.</div>:forwardTargets.map(item=><button disabled={actionBusy} key={item.user.id} onClick={()=>forwardTo(item.user)}><Avatar user={item.user} size={40}/><span><b>{item.user.name}</b><small>@{item.user.username}</small></span><Send size={17}/></button>)}</div></div></div>}
    {previewMedia&&<MediaPreview media={previewMedia} onClose={()=>setPreviewMedia(null)}/>} 
    {groupInfoOpen&&<GroupChatInfo group={target} friends={friends} onClose={()=>setGroupInfoOpen(false)} onChanged={onChanged} onApplied={updated=>{onGroupSettingsChanged?.(updated);setSettingsNotice("Group customization applied");setTimeout(()=>setSettingsNotice(""),2600)}} onLeave={async()=>{if(!await confirmDialog({title:"Leave group chat?",message:"You will stop receiving messages from this group.",confirmLabel:"Leave"}))return;try{await api(`/api/chat/group-conversations/${target.group_chat_id}/members/${me.id}`,{method:"DELETE"});setGroupInfoOpen(false);location.assign("/messages")}catch(e){alert(e.message)}}}/>} 
    {directInfoOpen&&<DirectChatInfo target={target} me={me} messages={messages} openProfile={open} onClose={()=>setDirectInfoOpen(false)} onApplied={updated=>{setDirectSettings(updated);setSettingsNotice("Conversation settings applied");setTimeout(()=>setSettingsNotice(""),2600);onChanged?.()}}/>}
  </div>
}

function SettingsPage({user,onUserUpdated,onAccountClosed,openProfile,openMessage,theme="dark",onThemeChange,language="en",onLanguageChange,timezone="auto",onTimezoneChange,notificationPrefs=MESSAGE_NOTIFICATION_DEFAULTS,onNotificationPrefsChange}){
  const[f,setF]=useState({current_password:"",new_password:"",confirm_password:""}),[msg,setMsg]=useState(""),[err,setErr]=useState(""),[busy,setBusy]=useState(false);
  const[username,setUsername]=useState(user.username||"");
  const[usernameStatus,setUsernameStatus]=useState(null);
  const[usernameMsg,setUsernameMsg]=useState("");
  const[usernameErr,setUsernameErr]=useState("");
  const[usernameBusy,setUsernameBusy]=useState(false);
  const[blockedUsers,setBlockedUsers]=useState([]),[restrictedUsers,setRestrictedUsers]=useState([]),[privacyBusy,setPrivacyBusy]=useState(null),[privacyError,setPrivacyError]=useState("");
  const[activeStatus,setActiveStatus]=useState(user.active_status_enabled!==false),[activeStatusBusy,setActiveStatusBusy]=useState(false),[activeStatusMessage,setActiveStatusMessage]=useState("");
  const[profilePrivacy,setProfilePrivacy]=useState(defaultProfilePrivacy),[privacyCheckup,setPrivacyCheckup]=useState(null),[profilePrivacyBusy,setProfilePrivacyBusy]=useState(false),[profilePrivacyMessage,setProfilePrivacyMessage]=useState("");
  const[lifecycle,setLifecycle]=useState(null),[lifecyclePassword,setLifecyclePassword]=useState(""),[lifecycleBusy,setLifecycleBusy]=useState(false),[lifecycleMessage,setLifecycleMessage]=useState("");
  const[exportForm,setExportForm]=useState({format:"json",date_from:"",date_to:"",categories:["profile","posts","comments","reactions","messages","friends","groups","activity","media"]});
  const[historyForm,setHistoryForm]=useState({category:"search",date_from:"",date_to:""});
  const[sessions,setSessions]=useState([]),[securityBusy,setSecurityBusy]=useState(false),[securityMessage,setSecurityMessage]=useState(""),[securityError,setSecurityError]=useState("");
  const[securityPassword,setSecurityPassword]=useState(""),[twoFactorSetup,setTwoFactorSetup]=useState(null),[twoFactorCode,setTwoFactorCode]=useState(""),[recoveryCodes,setRecoveryCodes]=useState([]);

  useEffect(()=>{api("/api/users/me/username-status").then(setUsernameStatus).catch(e=>setUsernameErr(e.message))},[user.id]);
  async function loadPrivacyLists(){
    try{const[blocked,restricted]=await Promise.all([api("/api/users/me/blocked"),api("/api/chat/restricted")]);setBlockedUsers(Array.isArray(blocked)?blocked:[]);setRestrictedUsers(Array.isArray(restricted)?restricted:[]);setPrivacyError("")}
    catch(e){setPrivacyError(e.message)}
  }
  useEffect(()=>{loadPrivacyLists()},[user.id]);
  useEffect(()=>{Promise.all([api("/api/users/me/privacy-settings"),api("/api/users/me/privacy/checkup")]).then(([settings,checkup])=>{setProfilePrivacy(settings);setPrivacyCheckup(checkup)}).catch(e=>setPrivacyError(e.message))},[user.id]);
  useEffect(()=>{api("/api/account/lifecycle").then(setLifecycle).catch(e=>setPrivacyError(e.message))},[user.id]);
  useEffect(()=>{setActiveStatus(user.active_status_enabled!==false)},[user.active_status_enabled]);
  async function loadSessions(){try{setSessions(await api("/api/auth/sessions"));setSecurityError("")}catch(e){setSecurityError(e.message)}}
  useEffect(()=>{loadSessions()},[user.id]);
  async function resendVerification(){setSecurityBusy(true);setSecurityError("");try{setSecurityMessage((await api("/api/auth/email/resend",{method:"POST"})).message)}catch(e){setSecurityError(e.message)}finally{setSecurityBusy(false)}}
  async function revokeSession(item){if(!await confirmDialog({variant:"confirm",title:"Log out this device?",message:`End the session for ${item.device_name||"this device"}?`,confirmLabel:"Log out"}))return;setSecurityBusy(true);try{const d=await api(`/api/auth/sessions/${item.id}`,{method:"DELETE",authRetry:false});if(d.current){authService.clear();onAccountClosed?.();return}await loadSessions();setSecurityMessage(d.message)}catch(e){setSecurityError(e.message)}finally{setSecurityBusy(false)}}
  async function logoutAllDevices(){if(!await confirmDialog({variant:"confirm",title:"Log out all devices?",message:"Every SocialN session, including this browser, will be revoked.",confirmLabel:"Log out all"}))return;setSecurityBusy(true);try{await api("/api/auth/logout-all",{method:"POST",authRetry:false});authService.clear();onAccountClosed?.()}catch(e){setSecurityError(e.message);setSecurityBusy(false)}}
  async function beginTwoFactor(){if(!securityPassword){setSecurityError("Enter your current password first.");return}setSecurityBusy(true);setSecurityError("");try{setTwoFactorSetup(await api("/api/auth/2fa/setup",{method:"POST",body:JSON.stringify({password:securityPassword})}));setTwoFactorCode("")}catch(e){setSecurityError(e.message)}finally{setSecurityBusy(false)}}
  async function confirmTwoFactor(){setSecurityBusy(true);setSecurityError("");try{const d=await api("/api/auth/2fa/confirm",{method:"POST",body:JSON.stringify({code:twoFactorCode})});setRecoveryCodes(d.recovery_codes||[]);setTwoFactorSetup(null);setTwoFactorCode("");setSecurityPassword("");setSecurityMessage(d.message);onUserUpdated?.({...user,two_factor_enabled:true})}catch(e){setSecurityError(e.message)}finally{setSecurityBusy(false)}}
  async function disableTwoFactor(){if(!securityPassword){setSecurityError("Enter your current password first.");return}if(!await confirmDialog({title:"Disable two-factor authentication?",message:"Your account will rely on its password alone and all sessions will be signed out.",confirmLabel:"Disable"}))return;setSecurityBusy(true);try{await api("/api/auth/2fa/disable",{method:"POST",body:JSON.stringify({password:securityPassword}),authRetry:false});authService.clear();onAccountClosed?.()}catch(e){setSecurityError(e.message);setSecurityBusy(false)}}

  async function unblock(item){
    if(!await confirmDialog({title:"Unblock this person?",message:`${item.name} will be able to find your profile and contact you again.`,confirmLabel:"Unblock",cancelLabel:"Keep blocked"}))return;
    setPrivacyBusy(`block-${item.id}`);try{await api(`/api/users/${item.id}/block`,{method:"DELETE"});setBlockedUsers(rows=>rows.filter(row=>row.id!==item.id))}catch(e){setPrivacyError(e.message)}finally{setPrivacyBusy(null)}
  }
  async function unrestrict(item){
    if(!await confirmDialog({title:"Remove restriction?",message:`Move ${item.name}'s conversation back to your regular messages?`,confirmLabel:"Unrestrict",cancelLabel:"Keep restricted"}))return;
    setPrivacyBusy(`restrict-${item.id}`);try{await api(`/api/chat/restricted/${item.id}`,{method:"DELETE"});setRestrictedUsers(rows=>rows.filter(row=>row.id!==item.id))}catch(e){setPrivacyError(e.message)}finally{setPrivacyBusy(null)}
  }
  async function changeActiveStatus(){
    const enabled=!activeStatus;
    const accepted=await confirmDialog({title:enabled?"Turn on Active Status?":"Turn off Active Status?",message:enabled?"You and other people with Active Status turned on will be able to see when each other are online or were recently active.":"Other people will not see when you are online or were recently active. You also will not be able to see their activity status.",detail:"This setting follows mutual visibility: both people must have Active Status turned on.",confirmLabel:enabled?"Turn on":"Turn off",cancelLabel:"Cancel"});
    if(!accepted)return;
    setActiveStatusBusy(true);setActiveStatusMessage("");
    try{const updated=await api("/api/users/me/active-status",{method:"PUT",body:JSON.stringify({enabled})});setActiveStatus(updated.active_status_enabled!==false);onUserUpdated?.(updated);setActiveStatusMessage(enabled?"Active Status is on.":"Active Status is off.")}
    catch(e){setPrivacyError(e.message)}finally{setActiveStatusBusy(false)}
  }

  async function saveProfilePrivacy(){
    if(!await confirmChange("Save privacy settings?","Apply these audiences to your profile information?","People outside each selected audience will no longer receive those fields from the API."))return;
    setProfilePrivacyBusy(true);setProfilePrivacyMessage("");try{const updated=await api("/api/users/me/privacy-settings",{method:"PUT",body:JSON.stringify(profilePrivacy)});setProfilePrivacy(updated);setPrivacyCheckup(await api("/api/users/me/privacy/checkup"));setProfilePrivacyMessage("Privacy settings applied.")}catch(e){setPrivacyError(e.message)}finally{setProfilePrivacyBusy(false)}
  }
  async function limitOldPosts(){
    if(!await confirmDialog({title:"Limit past posts?",message:"All existing posts except Only me posts will be changed to Friends.",detail:"Custom, follower and public audiences on old posts will be removed. You can still edit individual posts later.",confirmLabel:"Limit old posts"}))return;
    setProfilePrivacyBusy(true);try{const result=await api("/api/users/me/privacy/limit-old-posts",{method:"POST"});setProfilePrivacyMessage(`${result.updated_count} past posts were limited to Friends.`);setPrivacyCheckup(await api("/api/users/me/privacy/checkup"))}catch(e){setPrivacyError(e.message)}finally{setProfilePrivacyBusy(false)}
  }

  function toggleExportCategory(category){setExportForm(current=>({...current,categories:current.categories.includes(category)?current.categories.filter(item=>item!==category):[...current.categories,category]}))}
  async function downloadData(){
    if(!exportForm.categories.length){setPrivacyError("Choose at least one data category.");return}
    setLifecycleBusy(true);setLifecycleMessage("");setPrivacyError("");
    try{
      const response=await fetch(`${API}/api/account/export`,{method:"POST",headers:{"Authorization":`Bearer ${tok()}`,"Content-Type":"application/json"},body:JSON.stringify({...exportForm,date_from:exportForm.date_from||null,date_to:exportForm.date_to||null})});
      if(!response.ok){const value=await response.json().catch(()=>({}));throw Error(value.detail||"Could not create the export")}
      const blob=await response.blob(),url=URL.createObjectURL(blob),link=document.createElement("a"),disposition=response.headers.get("content-disposition")||"",match=disposition.match(/filename="([^"]+)"/);link.href=url;link.download=match?.[1]||`socialn-data.${exportForm.format}`;document.body.appendChild(link);link.click();link.remove();URL.revokeObjectURL(url);setLifecycleMessage("Your data export was downloaded.");
    }catch(e){setPrivacyError(e.message)}finally{setLifecycleBusy(false)}
  }
  async function clearHistory(){
    if(!await confirmDialog({title:"Clear activity history?",message:`Delete ${historyForm.category} history for the selected period?`,detail:"This removes the records from your Activity log and cannot be undone.",confirmLabel:"Clear history"}))return;
    setLifecycleBusy(true);setLifecycleMessage("");try{const result=await api("/api/account/activity",{method:"DELETE",body:JSON.stringify({...historyForm,date_from:historyForm.date_from||null,date_to:historyForm.date_to||null})});setLifecycleMessage(`${result.deleted_count} activity records deleted.`)}catch(e){setPrivacyError(e.message)}finally{setLifecycleBusy(false)}
  }
  async function closeAccount(mode){
    if(!lifecyclePassword){setPrivacyError("Enter your current password first.");return}
    const deleting=mode==="delete",accepted=await confirmDialog({title:deleting?"Schedule account deletion?":"Deactivate your account?",message:deleting?`Your account will be permanently deleted after ${lifecycle?.deletion_grace_days||30} days unless you sign in again.`:"Your profile and content will be hidden until you sign in again.",detail:deleting?"After permanent deletion, live media is removed. Backup copies expire according to the retention policy.":"Signing in again immediately reactivates the account.",confirmLabel:deleting?"Schedule deletion":"Deactivate"});
    if(!accepted)return;setLifecycleBusy(true);try{await api(`/api/account/${mode}`,{method:"POST",body:JSON.stringify({password:lifecyclePassword})});authService.clear();onAccountClosed?.()}catch(e){setPrivacyError(e.message);setLifecycleBusy(false)}
  }

  async function changeNotificationPref(key,value){
    if(key==="desktop"&&value){
      if(!("Notification" in window)){setPrivacyError("Desktop notifications are not supported by this browser.");return}
      const permission=Notification.permission==="granted"?"granted":await Notification.requestPermission();
      if(permission!=="granted"){setPrivacyError("Desktop notification permission was not granted.");return}
    }
    onNotificationPrefsChange?.({...notificationPrefs,[key]:value});
  }

  async function confirmChange(title,message,detail){return confirmDialog({variant:"confirm",title,message,detail,confirmLabel:"Apply changes",cancelLabel:"Cancel"})}
  async function changeTheme(value){if(value===theme)return;if(await confirmChange("Change appearance?",`Switch SocialN to ${value==="light"?"Light":"Dark"} mode?`,"The new appearance will be saved on this browser."))onThemeChange?.(value)}
  async function changeLanguage(value){if(value===language)return;const label=LANGUAGES.find(item=>item.code===value)?.label||value;if(await confirmChange("Change language?",`Use ${label} across SocialN?`,"Navigation and supported interface text will update immediately."))onLanguageChange?.(value)}
  async function changeTimezone(value){if(value===timezone)return;const label=TIMEZONES.find(item=>item[0]===value)?.[1]||value;if(await confirmChange("Change time zone?",`Use ${label}?`,"All displayed dates and times across SocialN will be converted to this time zone."))onTimezoneChange?.(value)}

  async function submit(e){
    e.preventDefault();
    setMsg("");setErr("");

    if(f.new_password.length<8){setErr("New password must be at least 8 characters.");return}
    if(f.new_password!==f.confirm_password){setErr("Password confirmation does not match.");return}
    if(!await confirmChange("Change password?","Do you want to update your SocialN password?","You will need the new password the next time you sign in."))return;

    setBusy(true);
    try{
      const d=await api("/api/users/me/password",{
        method:"PUT",
        body:JSON.stringify({current_password:f.current_password,new_password:f.new_password})
      });
      setMsg(d.message||"Password changed successfully.");
      setF({current_password:"",new_password:"",confirm_password:""});
      if(d.reauthenticate){authService.clear();window.setTimeout(()=>onAccountClosed?.(),700)}
    }catch(e){setErr(e.message)}
    finally{setBusy(false)}
  }

  async function submitUsername(e){
    e.preventDefault();setUsernameMsg("");setUsernameErr("");
    const value=username.trim().toLowerCase();
    if(!/^[a-z0-9._]{3,80}$/.test(value)){setUsernameErr("Use 3–80 letters, numbers, dots or underscores.");return}
    if(!await confirmChange("Change username?",`Change @${user.username} to @${value}?`,"Your profile URL will change, and you cannot change the username again for 30 days."))return;
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
        <button type="button" role="radio" aria-checked={theme==="light"} className={`theme-option ${theme==="light"?"selected":""}`} onClick={()=>changeTheme("light")}><Sun size={22}/><span><b>Light</b><small>Bright background</small></span><i>{theme==="light"?"✓":""}</i></button>
        <button type="button" role="radio" aria-checked={theme==="dark"} className={`theme-option ${theme==="dark"?"selected":""}`} onClick={()=>changeTheme("dark")}><Moon size={22}/><span><b>Dark</b><small>Easy on the eyes</small></span><i>{theme==="dark"?"✓":""}</i></button>
      </div>
    </div>
    <div className="settings-section language-settings">
      <h3>Language</h3>
      <p className="muted small">Choose the language used across SocialN.</p>
      <LanguagePicker value={language} onChange={changeLanguage}/>
    </div>
    <div className="settings-section timezone-settings">
      <h3>Time zone</h3>
      <p className="muted small">Apply this time zone to posts, notifications, activity history and all dates across SocialN.</p>
      <label>Time zone<select value={timezone} onChange={e=>changeTimezone(e.target.value)}>{TIMEZONES.map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label>
      <div className="timezone-preview"><span>Current time</span><b>{formatDateTime(new Date().toISOString())}</b></div>
    </div>
    <div className="settings-section active-status-settings">
      <div className="active-status-copy"><div><h3>Active Status</h3><p className="muted small">Show when you're active or recently active. If this is off, you won't see other people's activity status either.</p></div><span className={`active-status-preview ${activeStatus?"on":"off"}`}><i/>{activeStatus?"On":"Off"}</span></div>
      <label className="active-status-toggle"><span><b>Show when you're active</b><small>Mutual visibility applies to online and last active information.</small></span><input type="checkbox" role="switch" checked={activeStatus} disabled={activeStatusBusy} onChange={changeActiveStatus}/></label>
      {activeStatusMessage&&<div className="success-notice">{activeStatusMessage}</div>}
    </div>
    <div className="settings-section message-notification-settings">
      <h3>Push notifications</h3>
      <p className="muted small">Control Metro-style alerts for messages, friend requests, comments, reactions and other activity on this browser.</p>
      <label className="settings-switch-row"><span><b>In-app notifications</b><small>Show a Metro notification tile while SocialN is open.</small></span><input type="checkbox" role="switch" checked={notificationPrefs.enabled} onChange={e=>changeNotificationPref("enabled",e.target.checked)}/></label>
      <label className="settings-switch-row"><span><b>Desktop notifications</b><small>Show an operating-system notification when this tab is in the background.</small></span><input type="checkbox" role="switch" checked={notificationPrefs.desktop} disabled={!notificationPrefs.enabled} onChange={e=>changeNotificationPref("desktop",e.target.checked)}/></label>
      <label className="settings-switch-row"><span><b>Notification sound</b><small>Play a short sound for messages that are not muted.</small></span><input type="checkbox" role="switch" checked={notificationPrefs.sound} disabled={!notificationPrefs.enabled} onChange={e=>changeNotificationPref("sound",e.target.checked)}/></label>
      <div className="message-notification-grid"><label>Message preview<select value={notificationPrefs.preview} onChange={e=>changeNotificationPref("preview",e.target.value)}><option value="full">Sender and message</option><option value="sender">Sender only</option><option value="hidden">Hide all details</option></select></label><label>Display duration<select value={notificationPrefs.duration} onChange={e=>changeNotificationPref("duration",Number(e.target.value))}><option value={4000}>4 seconds</option><option value={6000}>6 seconds</option><option value={8000}>8 seconds</option></select></label></div>
      {"Notification" in window&&<div className="notification-permission">Browser permission: <b>{Notification.permission}</b></div>}
    </div>
    <div className="settings-section advanced-privacy-settings">
      <h3>Privacy checkup</h3>
      <p className="muted small">Control who can see individual profile fields and review the audience of your posts.</p>
      <div className="profile-privacy-grid">{[["dob","Birthday"],["hometown","Hometown"],["relationship","Relationship"],["albums","Albums"],["friends_list","Friends list"]].map(([key,label])=><label key={key}><span>{label}</span><AudienceSelector privacy={profilePrivacy[key]?.audience||"friends"} onPrivacyChange={value=>setProfilePrivacy({...profilePrivacy,[key]:{...profilePrivacy[key],audience:value}})} audience={profilePrivacy[key]||emptyAudience()} onAudienceChange={value=>setProfilePrivacy({...profilePrivacy,[key]:{...profilePrivacy[key],...value}})} compact/></label>)}</div>
      <div className="privacy-checkup-summary"><h4>Current exposure</h4>{privacyCheckup?.recommendations?.map((item,index)=><p key={index}>{item}</p>)}{privacyCheckup&&<div className="privacy-counts">{Object.entries(privacyCheckup.post_counts||{}).filter(([,count])=>count>0).map(([key,count])=><span key={key}><b>{count}</b> {audienceLabel(key)}</span>)}</div>}</div>
      {profilePrivacyMessage&&<div className="success-notice">{profilePrivacyMessage}</div>}
      <div className="privacy-settings-actions"><button className="primary" disabled={profilePrivacyBusy} onClick={saveProfilePrivacy}>{profilePrivacyBusy?"Applying…":"Save privacy settings"}</button><button className="secondary" disabled={profilePrivacyBusy} onClick={limitOldPosts}>Limit past posts</button></div>
    </div>
    <div className="settings-section privacy-management">
      <h3>Blocking &amp; restrictions</h3>
      <p className="muted small">Review people you have blocked and conversations you have restricted.</p>
      {privacyError&&<div className="error">{privacyError}</div>}
      <div className="privacy-list-group"><div className="privacy-list-title"><span><ShieldBan size={19}/> Blocked people</span><b>{blockedUsers.length}</b></div>
        {blockedUsers.length===0?<div className="muted privacy-empty">You haven't blocked anyone.</div>:blockedUsers.map(item=><div className="privacy-user-row" key={item.id}><button className="privacy-user-main" onClick={()=>openProfile?.(item.id)}><Avatar user={item} size={44}/><span><b>{item.name}</b><small>@{item.username}</small></span></button><button className="secondary" disabled={privacyBusy===`block-${item.id}`} onClick={()=>unblock(item)}>{privacyBusy===`block-${item.id}`?"Updating...":"Unblock"}</button></div>)}
      </div>
      <div className="privacy-list-group"><div className="privacy-list-title"><span><MessageCircle size={19}/> Restricted conversations</span><b>{restrictedUsers.length}</b></div>
        {restrictedUsers.length===0?<div className="muted privacy-empty">You haven't restricted any conversations.</div>:restrictedUsers.map(item=><div className="privacy-user-row" key={item.id}><button className="privacy-user-main" onClick={()=>openProfile?.(item.id)}><Avatar user={item} size={44}/><span><b>{item.name}</b><small>@{item.username}</small></span></button><div className="privacy-user-actions"><button className="secondary" onClick={()=>openMessage?.(item)}>View messages</button><button className="secondary" disabled={privacyBusy===`restrict-${item.id}`} onClick={()=>unrestrict(item)}>{privacyBusy===`restrict-${item.id}`?"Updating...":"Unrestrict"}</button></div></div>)}
      </div>
    </div>
    <div className="settings-section data-lifecycle-settings">
      <h3>Your information and account</h3>
      <p className="muted small">Download your information, clear selected history, or control the lifecycle of your account.</p>
      <div className="data-tool-card"><div><h4><Download size={18}/> Download your information</h4><p className="muted small">Choose a format, date range and the data categories to include.</p></div><div className="data-export-controls"><label>Format<select value={exportForm.format} onChange={e=>setExportForm({...exportForm,format:e.target.value})}><option value="json">JSON</option><option value="html">HTML</option></select></label><label>From<input type="date" value={exportForm.date_from} onChange={e=>setExportForm({...exportForm,date_from:e.target.value})}/></label><label>To<input type="date" value={exportForm.date_to} onChange={e=>setExportForm({...exportForm,date_to:e.target.value})}/></label></div><div className="export-categories">{[["profile","Profile"],["posts","Posts"],["comments","Comments"],["reactions","Reactions"],["messages","Messages"],["friends","Friends"],["groups","Groups"],["activity","Activity"],["media","Media"]].map(([key,label])=><label key={key}><input type="checkbox" checked={exportForm.categories.includes(key)} onChange={()=>toggleExportCategory(key)}/><span>{label}</span></label>)}</div><button className="primary" disabled={lifecycleBusy} onClick={downloadData}><Download size={17}/> Download export</button></div>
      <div className="data-tool-card"><div><h4><History size={18}/> Clear history</h4><p className="muted small">Delete search, login or grouped activity records for an optional period.</p></div><div className="data-export-controls"><label>History type<select value={historyForm.category} onChange={e=>setHistoryForm({...historyForm,category:e.target.value})}><option value="search">Search history</option><option value="login">Login history</option><option value="posts">Posts &amp; interactions activity</option><option value="profile">Profile activity</option><option value="friends">Friendship activity</option><option value="security">Security activity</option><option value="all">All activity</option></select></label><label>From<input type="date" value={historyForm.date_from} onChange={e=>setHistoryForm({...historyForm,date_from:e.target.value})}/></label><label>To<input type="date" value={historyForm.date_to} onChange={e=>setHistoryForm({...historyForm,date_to:e.target.value})}/></label></div><button className="secondary" disabled={lifecycleBusy} onClick={clearHistory}>Clear selected history</button></div>
      <div className="data-retention-note"><b>Deletion and backup policy</b><p>{lifecycle?.policy||"Live data is erased after the recovery period. Backup copies expire under the configured retention policy."}</p><small>Recovery period: {lifecycle?.deletion_grace_days||30} days · Backup retention: up to {lifecycle?.backup_retention_days||30} days</small></div>
      {lifecycleMessage&&<div className="success-notice">{lifecycleMessage}</div>}
      <div className="account-danger-zone"><h4>Deactivate or delete account</h4><label>Current password<input type="password" autoComplete="current-password" value={lifecyclePassword} onChange={e=>setLifecyclePassword(e.target.value)} placeholder="Required to continue"/></label><div><button className="secondary" disabled={lifecycleBusy} onClick={()=>closeAccount("deactivate")}>Deactivate account</button><button className="danger" disabled={lifecycleBusy} onClick={()=>closeAccount("delete")}>Delete account</button></div></div>
    </div>
    <div className="settings-section account-security-settings">
      <h3>Account security</h3>
      <p className="muted small">Verify your email, protect sign-in with an authenticator app, and review active device sessions.</p>
      {securityError&&<div className="error">{securityError}</div>}{securityMessage&&<div className="success-notice">{securityMessage}</div>}
      <div className="security-status-grid">
        <div className="security-status-card"><span><b>Email verification</b><small>{user.email_verified?"Your email address is verified.":"Verify ownership of your email address."}</small></span><button className="secondary" disabled={securityBusy||user.email_verified} onClick={resendVerification}>{user.email_verified?"Verified":"Send verification email"}</button></div>
        <div className="security-status-card"><span><b>Authenticator app (TOTP)</b><small>{user.two_factor_enabled?"A second factor is required when you sign in.":"Use Google Authenticator, Microsoft Authenticator or another TOTP app."}</small></span></div>
      </div>
      <label>Current password<input type="password" autoComplete="current-password" value={securityPassword} onChange={e=>setSecurityPassword(e.target.value)} placeholder="Required for 2FA changes"/></label>
      {!user.two_factor_enabled&&!twoFactorSetup&&<button className="primary" disabled={securityBusy} onClick={beginTwoFactor}>Set up two-factor authentication</button>}
      {user.two_factor_enabled&&<button className="danger" disabled={securityBusy} onClick={disableTwoFactor}>Disable two-factor authentication</button>}
      {twoFactorSetup&&<div className="two-factor-setup"><h4>Connect your authenticator app</h4><p>Open your authenticator app and enter this setup key:</p><code>{twoFactorSetup.secret}</code><small className="muted">You can also paste the supplied otpauth URI into an app that supports it.</small><details><summary>Show otpauth URI</summary><code>{twoFactorSetup.otpauth_url}</code></details><label>6-digit code<input inputMode="numeric" autoComplete="one-time-code" value={twoFactorCode} onChange={e=>setTwoFactorCode(e.target.value)} placeholder="123456"/></label><button className="primary" disabled={securityBusy||twoFactorCode.length<6} onClick={confirmTwoFactor}>Confirm and enable</button></div>}
      {recoveryCodes.length>0&&<div className="recovery-codes"><h4>Save your recovery codes now</h4><p>Each code works once. Store them somewhere private; they will not be shown again.</p><div>{recoveryCodes.map(code=><code key={code}>{code}</code>)}</div></div>}
      <div className="device-sessions"><div className="section-head"><div><h4>Where you're logged in</h4><p className="muted small">Revoke any browser or device you no longer recognize.</p></div><button className="secondary" disabled={securityBusy||sessions.length===0} onClick={logoutAllDevices}>Log out all</button></div>{sessions.map(item=><div className="session-row" key={item.id}><div><b>{item.device_name||"Unknown device"} {item.current&&<span className="count-chip">Current</span>}</b><small>{item.ip_address||"Unknown IP"} · Active {formatDateTime(item.last_seen_at)}</small></div><button className="secondary" disabled={securityBusy} onClick={()=>revokeSession(item)}>Log out</button></div>)}</div>
    </div>
    <div className="settings-section">
      <h3>Change username</h3>
      <p className="muted small">Your profile address will become localhost:5173/{username||"username"}. You can change your username only once every 30 days.</p>
      <form onSubmit={submitUsername}>
        <label>Username<input value={username} disabled={usernameStatus&&!usernameStatus.can_change} onChange={e=>setUsername(e.target.value)} autoComplete="username"/></label>
        {usernameStatus&&!usernameStatus.can_change&&<div className="username-cooldown">You can change it again on <b>{formatDateTime(usernameStatus.next_change_at)}</b>.</div>}
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

const ACTIVITY_FILTERS=[
  ["all","All activity"],["posts","Posts & interactions"],["profile","Profile changes"],
  ["friends","Friends"],["search","Search history"],["security","Login & security"]
];
function ActivityLogPage({openProfile}){
  const[category,setCategory]=useState("all"),[items,setItems]=useState([]),[total,setTotal]=useState(0),[loading,setLoading]=useState(true),[error,setError]=useState("");
  async function load(nextCategory=category){setLoading(true);setError("");try{const d=await api(`/api/activity?category=${encodeURIComponent(nextCategory)}&limit=100`);setItems(d.items||[]);setTotal(d.total||0)}catch(e){setError(e.message)}finally{setLoading(false)}}
  useEffect(()=>{load(category)},[category]);
  const icon={posts:"👍",profile:"👤",friends:"👥",search:"🔎",security:"🔐"};
  return <div className="activity-page"><div className="card activity-head"><div><h1>Activity log</h1><p className="muted">Review actions and account history visible only to you.</p></div><span className="count-chip">{total}</span></div><div className="activity-layout"><aside className="card activity-filters">{ACTIVITY_FILTERS.map(([key,label])=><button key={key} className={category===key?"active":""} onClick={()=>setCategory(key)}>{key==="all"?<History size={18}/>:<span>{icon[key]}</span>}{label}</button>)}</aside><section className="card activity-list">{error&&<div className="error">{error}</div>}{loading?<div className="empty compact">Loading activity...</div>:items.length===0?<div className="empty compact">No activity in this category yet.</div>:items.map(item=><article className="activity-row" key={item.id}><div className="activity-icon">{icon[item.category]||"•"}</div><div className="activity-copy"><b>{item.description}</b><small>{formatDateTime(item.created_at)}</small>{item.category==="security"&&(item.ip_address||item.user_agent)&&<details><summary>Login details</summary><div>{item.ip_address&&<>IP: {item.ip_address}<br/></>}{item.user_agent||"Unknown device"}</div></details>}</div>{item.target_user&&<button className="activity-person" onClick={()=>openProfile?.(item.target_user.id)}><Avatar user={item.target_user} size={34}/><span>{item.target_user.name}</span></button>}</article>)}</section></div></div>
}
function App(){const[user,setUser]=useState(null),[view,setView]=useState("home"),[feed,setFeed]=useState([]),[profile,setProfile]=useState(null),[friends,setFriends]=useState([]),[requests,setRequests]=useState([]),[suggestions,setSuggestions]=useState([]),[target,setTarget]=useState(null),[conversations,setConversations]=useState([]),[notifs,setNotifs]=useState([]),[unread,setUnread]=useState(0),[drop,setDrop]=useState(false),[search,setSearch]=useState(""),[results,setResults]=useState([]);useEffect(()=>{if(tok())api("/api/users/me").then(setUser)},[]);useEffect(()=>{if(!user)return;refresh();const w=new WebSocket(`${WS}/api/notifications/ws?token=${tok()}`);w.onopen=()=>w.send("ready");w.onmessage=()=>loadN();return()=>w.close()},[user?.id]);async function refresh(){loadFeed();setFriends(await api("/api/friends"));setRequests(await api("/api/friends/requests"));setSuggestions(await api("/api/users/suggestions/people"));loadN();loadC()}async function loadFeed(){try{const rows=await api("/api/posts");setFeed(Array.isArray(rows)?rows:[])}catch(e){console.error("Feed load failed",e);setFeed([])}}async function loadC(){try{const rows=await api("/api/chat/conversations");setConversations((Array.isArray(rows)?rows:[]).filter(c=>c&&c.user&&c.user.id))}catch(e){console.error("Conversation load failed",e);setConversations([])}}async function loadN(){const d=await api("/api/notifications");setNotifs(d.items);setUnread(d.unread_count)}async function open(id){const d=await api(`/api/users/${id}/profile`);setProfile(d);setView("profile");setDrop(false)}async function reload(id){await open(id);refresh()}function message(u){setTarget(u);setView("chat");loadC()}async function q(v){setSearch(v);setResults(v.trim()?await api(`/api/users/search?q=${encodeURIComponent(v)}`):[])}async function read(n){if(!n.is_read)await api(`/api/notifications/${n.id}/read`,{method:"POST"});if(n.type==="new_message"&&n.actor)message(n.actor);else if(n.type==="friend_request")setView("friends");else if(n.actor)open(n.actor.id);setDrop(false);loadN()}if(!user)return <Login onLogin={setUser}/>;return <div><header className="topbar"><div className="brand" onClick={()=>setView("home")}>Social<span>N</span></div><div className="search"><Search/><input value={search} onChange={e=>q(e.target.value)} placeholder="Search SocialN..."/>{results.length>0&&<div className="search-results">{results.map(u=><button key={u.id} onClick={()=>{open(u.id);setResults([]);setSearch("")}}><Avatar user={u}/><span>{u.name}<small>@{u.username}</small></span></button>)}</div>}</div><div className="top-actions"><button onClick={()=>setView("home")}><Home/></button><button onClick={()=>setView("friends")}><Users/></button><button onClick={()=>setView("chat")}><MessageCircle/></button><div className="notif-wrap"><button className="notification-btn" onClick={()=>setDrop(!drop)}><Bell/>{unread>0&&<span className="badge">{unread}</span>}</button>{drop&&<div className="notif-dropdown"><div className="notif-dropdown-head"><b>Notifications</b><button onClick={async()=>{await api("/api/notifications/read-all",{method:"POST"});loadN()}}>Mark all read</button></div><div className="notif-scroll">{notifs.slice(0,20).map(n=><button className={`notification-row ${n.is_read?"":"unread"}`} key={n.id} onClick={()=>read(n)}><Avatar user={n.actor}/><div className="notification-content">{n.message}<small>{formatDateTime(n.created_at)}</small></div></button>)}</div></div>}</div><button onClick={()=>setView("settings")}><Settings/></button><button onClick={()=>{localStorage.removeItem("socialn_token");setUser(null)}}><LogOut/></button></div></header><div className="layout"><aside className="sidebar"><button className="side-user" onClick={()=>open(user.id)}><Avatar user={user}/><b>{user.name}</b></button><button onClick={()=>setView("home")}><Home/> Home</button><button onClick={()=>open(user.id)}><Users/> Profile</button><button onClick={()=>setView("friends")}><UserCheck/> Friends {requests.length>0&&<span className="side-badge">{requests.length}</span>}</button><button onClick={()=>setView("chat")}><MessageCircle/> Messages</button><button onClick={()=>setView("settings")}><Settings/> Settings</button></aside><main className="main">{view==="home"&&<>
  <PostComposer onCreated={p=>setFeed(v=>[p,...v])}/>
  {feed.length===0?<div className="card empty">No posts yet. Create the first post.</div>:feed.map(p=><PostCard key={p.id} post={p} me={user} onOpenProfile={open} onUpdated={updated=>setFeed(v=>v.map(x=>x.id===updated.id?updated:x))} onDeleted={id=>setFeed(v=>v.filter(x=>x.id!==id))} onShared={shared=>setFeed(v=>[shared,...v])}/>) }
</>}{view==="profile"&&profile&&<Profile p={profile} me={user} reload={reload} message={message} open={open}/>} {view==="friends"&&<div className="friends-page"><div className="card friends-section"><h2>Friend requests</h2>{requests.map(r=><div className="request-row" key={r.id}><Avatar user={r.user} onClick={()=>open(r.user.id)}/><button className="name-block" onClick={()=>open(r.user.id)}><b>{r.user.name}</b></button><button className="primary" onClick={async()=>{await api(`/api/friends/${r.id}/accept`,{method:"POST"});refresh()}}>Confirm</button><button className="secondary" onClick={async()=>{await api(`/api/friends/${r.id}/reject`,{method:"POST"});refresh()}}>Delete</button></div>)}</div><div className="card friends-section"><h2>Your friends</h2><div className="people-grid">{friends.map(u=><div className="person" key={u.id}><Avatar user={u} onClick={()=>open(u.id)}/><button className="name-link" onClick={()=>open(u.id)}>{u.name}</button><button className="secondary" onClick={()=>message(u)}>Message</button></div>)}</div></div><div className="card friends-section"><h2>People you may know</h2><div className="people-grid">{suggestions.map(u=><div className="person" key={u.id}><Avatar user={u} onClick={()=>open(u.id)}/><button className="name-link" onClick={()=>open(u.id)}>{u.name}</button><small>{u.mutual_friends_count} mutual friends</small><button className="primary" onClick={async()=>{await api(`/api/friends/${u.id}`,{method:"POST"});refresh()}}>Add friend</button></div>)}</div></div></div>} {view==="chat"&&<div className="chat-layout"><div className="conversation-list card"><div className="conversation-title">Messages</div>{conversations.filter(c=>c?.user?.id).map(c=><button key={`c-${c.id}`} className={Number(target?.id)===Number(c.user.id)?"active":""} onClick={()=>setTarget(c.user)}><Avatar user={c.user}/><span>{c.user.name||c.user.username}<small>{c.last_message||`@${c.user.username}`}</small></span></button>)}{friends.filter(u=>u?.id&&!conversations.some(c=>Number(c?.user?.id)===Number(u.id))).map(u=><button key={`f-${u.id}`} className={Number(target?.id)===Number(u.id)?"active":""} onClick={()=>setTarget(u)}><Avatar user={u}/><span>{u.name}<small>Start a conversation</small></span></button>)}</div><Chat me={user} target={target} open={open} onChanged={loadC}/></div>} {view==="notifications"&&<div className="card notifications-page">{notifs.map(n=><button className="notification-row" key={n.id} onClick={()=>read(n)}>{n.message}</button>)}</div>} {view==="settings"&&<SettingsPage user={user}/>} </main></div></div>}
function GroupPostCard({group,item,onChanged,onPin}){
  const[comment,setComment]=useState(""),[menu,setMenu]=useState(false);
  async function react(reaction){try{await api(`/api/groups/${group.id}/posts/${item.id}/react`,{method:"POST",body:JSON.stringify({reaction})});onChanged()}catch(e){alert(e.message)}}
  async function addComment(e){e.preventDefault();if(!comment.trim())return;try{await api(`/api/groups/${group.id}/posts/${item.id}/comments`,{method:"POST",body:JSON.stringify({content:comment})});setComment("");onChanged()}catch(e){alert(e.message)}}
  async function share(){try{await api(`/api/groups/${group.id}/posts/${item.id}/share`,{method:"POST"});alert("Post shared to your timeline") }catch(e){alert(e.message)}}
  async function hide(){try{await api(`/api/groups/${group.id}/posts/${item.id}/hide`,{method:"POST"});setMenu(false);onChanged()}catch(e){alert(e.message)}}
  async function report(){if(!await confirmDialog({variant:"confirm",title:"Report this post?",message:"The report will be sent to this group's Admins and Moderators.",confirmLabel:"Send report"}))return;try{await api(`/api/groups/${group.id}/posts/${item.id}/report`,{method:"POST",body:JSON.stringify({reason:"Reported as potentially violating group rules"})});setMenu(false);alert("Report sent") }catch(e){alert(e.message)}}
  return <article className="card group-post"><div className="post-head">{item.author?<Avatar user={item.author}/>:<div className="anonymous-avatar">?</div>}<div><b>{item.author?.name||"Anonymous member"}</b><small>{formatDateTime(item.created_at)}</small></div>{item.is_pinned&&<span className="pinned-label"><Pin size={14}/> Pinned</span>}{item.can_moderate&&<button className="icon-btn" title={item.is_pinned?"Unpin":"Pin post"} onClick={()=>onPin(item)}><Pin size={18}/></button>}<div className="post-menu-wrap"><button className="icon-btn" aria-label="Post options" onClick={()=>setMenu(!menu)}><MoreHorizontal size={19}/></button>{menu&&<div className="post-menu"><button onClick={hide}>Hide post</button><button onClick={report}>Report post</button>{item.can_delete&&<button className="danger-link" onClick={async()=>{if(await confirmDialog({title:"Delete group post?",message:"This post will be permanently removed."})){await api(`/api/groups/${group.id}/posts/${item.id}`,{method:"DELETE"});onChanged()}}}><Trash2 size={16}/> Delete post</button>}</div>}</div></div><p>{item.content}</p>{item.shared_post&&<SharedPostPreview shared={item.shared_post}/>} {item.media_url&&(item.media_type==="video"?<video className="group-post-media" src={asset(item.media_url)} controls/>:item.media_type==="image"||item.media_type==="gif"?<img className="group-post-media" src={asset(item.media_url)}/>:<a className="group-file-link" href={asset(item.media_url)} target="_blank" rel="noreferrer"><FileText/> Open attached file</a>)}<div className="post-stats"><span className="reaction-summary">{Object.entries(item.reaction_counts||{}).filter(([,count])=>count).map(([key])=><span key={key}>{reactionInfo(key).emoji}</span>)} {item.reactions_count||0} reactions</span><span>{item.comments?.length||0} comments</span></div><div className="post-buttons"><div className="reaction-wrap"><button className={item.my_reaction?"active":""} onClick={()=>react(item.my_reaction||"like")}><span>{item.my_reaction?reactionInfo(item.my_reaction).emoji:<ThumbsUp size={18}/>}</span> {item.my_reaction?reactionInfo(item.my_reaction).label:"Like"}</button><div className="reaction-picker">{REACTIONS.map(option=><button key={option.key} title={option.label} onClick={()=>react(option.key)}>{option.emoji}</button>)}</div></div><button onClick={()=>document.getElementById(`group-comment-${item.id}`)?.focus()}><MessageSquare size={18}/> Comment</button>{item.can_share&&<button onClick={share}><Share2 size={18}/> Share</button>}</div><div className="group-comments">{(item.comments||[]).map(row=><div className="comment" key={row.id}><Avatar user={row.author} size={32}/><div className="comment-body"><b>{row.author.name}</b><div>{row.content}</div></div></div>)}</div><form className="comment-form" onSubmit={addComment}><input id={`group-comment-${item.id}`} value={comment} onChange={e=>setComment(e.target.value)} placeholder="Write a comment..."/><button className="primary"><Send size={17}/></button></form></article>
}

function GroupsPage({groupId,onOpen}){
  const[groups,setGroups]=useState([]),[group,setGroup]=useState(null),[posts,setPosts]=useState([]),[query,setQuery]=useState(""),[creating,setCreating]=useState(false),[error,setError]=useState("");
  const[form,setForm]=useState({name:"",description:"",rules:"",privacy:"public",visibility:"visible",group_type:"general",approval_questions:[""]});
  const[joinAnswers,setJoinAnswers]=useState([]),[post,setPost]=useState({content:"",is_anonymous:false}),[mediaFile,setMediaFile]=useState(null),[busy,setBusy]=useState(false),[coverBusy,setCoverBusy]=useState(false),[tab,setTab]=useState("about"),[memberQuery,setMemberQuery]=useState(""),[memberMenu,setMemberMenu]=useState(null),[addMemberOpen,setAddMemberOpen]=useState(false),[addMemberQuery,setAddMemberQuery]=useState(""),[addMemberResults,setAddMemberResults]=useState([]),[editingGroup,setEditingGroup]=useState(false),[groupDraft,setGroupDraft]=useState(null);
  async function loadList(q=query){try{setGroups(await api(`/api/groups?q=${encodeURIComponent(q)}`));setError("")}catch(e){setError(e.message)}}
  async function loadGroup(){if(!groupId){setGroup(null);loadList();return}try{const row=await api(`/api/groups/${groupId}`);setGroup(row);setJoinAnswers((row.approval_questions||[]).map(()=>""));if(row.can_view_content)setPosts(await api(`/api/groups/${groupId}/posts`));else setPosts([]);setError("")}catch(e){setError(e.message)}}
  useEffect(()=>{loadGroup()},[groupId]);
  async function create(e){e.preventDefault();setBusy(true);try{const row=await api("/api/groups",{method:"POST",body:JSON.stringify({...form,approval_questions:form.approval_questions.filter(x=>x.trim())})});setCreating(false);onOpen(row.id)}catch(e){setError(e.message)}finally{setBusy(false)}}
  async function join(){try{await api(`/api/groups/${group.id}/join`,{method:"POST",body:JSON.stringify({answers:joinAnswers})});loadGroup()}catch(e){setError(e.message)}}
  async function leave(){if(!await confirmDialog({variant:"confirm",title:"Leave group?",message:`You will no longer have access to member-only content in ${group.name}.`,confirmLabel:"Leave group"}))return;try{await api(`/api/groups/${group.id}/membership`,{method:"DELETE"});loadGroup()}catch(e){setError(e.message)}}
  async function publish(e){e.preventDefault();if(!post.content.trim()&&!mediaFile)return;try{let media_url=null,media_type="image";if(mediaFile){const body=new FormData();body.append("file",mediaFile);media_url=(await api("/api/upload",{method:"POST",body})).url;media_type=mediaFile.type.startsWith("video/")?"video":mediaFile.type.startsWith("image/")?"image":"file"}const created=await api(`/api/groups/${group.id}/posts`,{method:"POST",body:JSON.stringify({...post,media_url,media_type})});setPost({content:"",is_anonymous:false});setMediaFile(null);if(created.status==="pending")alert("Your post was submitted for Admin/Moderator approval.");loadGroup()}catch(e){setError(e.message)}}
  async function review(id,action){try{await api(`/api/groups/${group.id}/requests/${id}/${action}`,{method:"POST"});loadGroup()}catch(e){setError(e.message)}}
  async function togglePin(item){try{await api(`/api/groups/${group.id}/posts/${item.id}/pin`,{method:"POST"});loadGroup()}catch(e){setError(e.message)}}
  async function memberAction(item,action){setMemberMenu(null);try{if(action==="kick"||action==="ban"){if(!await confirmDialog({title:action==="ban"?"Ban member?":"Remove member?",message:`${item.name} will be removed from this group${action==="ban"?" and cannot rejoin":""}.`,confirmLabel:action==="ban"?"Ban":"Remove"}))return;await api(`/api/groups/${group.id}/members/${item.id}?ban=${action==="ban"}`,{method:"DELETE"})}else if(action.startsWith("role:")){await api(`/api/groups/${group.id}/members/${item.id}/role?role=${action.slice(5)}`,{method:"PUT"})}else{await api(`/api/groups/${group.id}/members/${item.id}/mute?hours=${action==="unmute"?0:action==="mute_week"?168:24}`,{method:"POST"})}loadGroup()}catch(e){setError(e.message)}}
  async function saveGroup(e){e.preventDefault();try{await api(`/api/groups/${group.id}`,{method:"PUT",body:JSON.stringify({...groupDraft,approval_questions:(groupDraft.approval_questions||[]).filter(Boolean)})});setEditingGroup(false);loadGroup()}catch(e){setError(e.message)}}
  async function changeCover(file){if(!file)return;setCoverBusy(true);setError("");try{const body=new FormData();body.append("file",file);const uploaded=await api("/api/upload",{method:"POST",body});await api(`/api/groups/${group.id}/cover`,{method:"PUT",body:JSON.stringify({cover_url:uploaded.url})});await loadGroup()}catch(e){setError(e.message)}finally{setCoverBusy(false)}}
  async function searchPeople(){try{const rows=await api(`/api/users/search?q=${encodeURIComponent(addMemberQuery.trim())}`),memberIds=new Set((group.members||[]).map(item=>Number(item.id)));setAddMemberResults(rows.filter(item=>!memberIds.has(Number(item.id))))}catch(e){setError(e.message)}}
  async function addMember(item){try{await api(`/api/groups/${group.id}/members/${item.id}`,{method:"POST"});setAddMemberResults(rows=>rows.filter(row=>row.id!==item.id));await loadGroup()}catch(e){setError(e.message)}}
  function postCard(item){return <GroupPostCard key={item.id} group={group} item={item} onChanged={loadGroup} onPin={togglePin}/>}
  if(!groupId)return <div className="groups-page"><div className="card groups-toolbar"><div><h1>Groups</h1><p>Connect and share with communities that matter to you.</p></div><button className="primary" onClick={()=>setCreating(!creating)}>{creating?"Cancel":"Create group"}</button></div>{creating&&<form className="card group-create" onSubmit={create}><h2>Create a group</h2><label>Group name<input required value={form.name} onChange={e=>setForm({...form,name:e.target.value})}/></label><label>Description<textarea value={form.description} onChange={e=>setForm({...form,description:e.target.value})}/></label><label>Group rules<textarea value={form.rules} onChange={e=>setForm({...form,rules:e.target.value})} placeholder="Write each rule on a new line..."/></label><div className="group-form-grid"><label>Privacy<select value={form.privacy} onChange={e=>setForm({...form,privacy:e.target.value})}><option value="public">Public</option><option value="private">Private</option></select></label><label>Visibility<select value={form.visibility} onChange={e=>setForm({...form,visibility:e.target.value})}><option value="visible">Visible</option><option value="hidden">Hidden</option></select></label><label>Group type<select value={form.group_type} onChange={e=>setForm({...form,group_type:e.target.value})}><option value="general">General</option><option value="social_learning">Social Learning</option><option value="buy_sell">Buy and Sell</option><option value="work_project">Work / Project</option></select></label></div><label>Membership questions (maximum 3){form.approval_questions.map((value,index)=><input key={index} value={value} placeholder={`Question ${index+1}`} onChange={e=>setForm({...form,approval_questions:form.approval_questions.map((x,i)=>i===index?e.target.value:x)})}/>)}</label>{form.approval_questions.length<3&&<button type="button" className="secondary" onClick={()=>setForm({...form,approval_questions:[...form.approval_questions,""]})}>Add question</button>}<button className="primary" disabled={busy}>Create group</button></form>}<div className="card group-discovery"><div className="group-search"><Search size={19}/><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search groups..."/><button onClick={()=>loadList(query)}>Search</button></div>{error&&<div className="error">{error}</div>}<div className="group-grid">{groups.map(item=><button className="group-card" key={item.id} onClick={()=>onOpen(item.id)}><div className="group-cover">{item.cover_url?<img src={asset(item.cover_url)}/>:<Users size={42}/>}</div><b>{item.name}</b><span>{item.privacy==="private"?"🔒 Private":"🌐 Public"} · {item.member_count} members</span><small>{item.description||"No description"}</small></button>)}</div></div></div>;
  if(!group)return <div className="card empty">{error||"Loading group..."}</div>;
  const mediaPosts=posts.filter(item=>["image","video","gif"].includes(item.media_type)&&item.media_url),filePosts=posts.filter(item=>item.media_type==="file"&&item.media_url),filteredMembers=(group.members||[]).filter(item=>!memberQuery.trim()||`${item.name} ${item.username}`.toLowerCase().includes(memberQuery.trim().toLowerCase()));
  return <div className="groups-page group-detail"><section className="card group-hero">
<div className="group-hero-cover">{group.cover_url?<img src={asset(group.cover_url)}/>:<Users size={70}/>} {group.my_role==="admin"&&<label className={`group-cover-change ${coverBusy?"busy":""}`}><Camera size={18}/>{coverBusy?"Uploading...":"Change cover photo"}<input hidden type="file" accept="image/*" disabled={coverBusy} onChange={e=>{changeCover(e.target.files?.[0]);e.target.value=""}}/></label>}</div>
<div className="group-hero-info"><div><h1>{group.name}</h1><p>{group.privacy==="private"?"🔒 Private group":"🌐 Public group"} · {group.visibility==="hidden"?"Hidden":"Visible"} · {group.member_count} members</p></div>{group.membership_status==="member"?<button className="secondary" onClick={leave}>Joined · Leave</button>:group.membership_status==="pending"?<button className="secondary" disabled>Request pending</button>:<button className="primary" onClick={join}>Join group</button>}</div><p>{group.description||"No description"}</p><nav className="group-tabs">{[["about","About"],["discussion","Discussion"],["featured","Featured"],["people","People"],["media","Media"],["files","Files"]].map(([key,label])=><button key={key} className={tab===key?"active":""} onClick={()=>setTab(key)}>{label}</button>)}</nav></section>{error&&<div className="error">{error}</div>}{group.membership_status==="none"&&group.approval_questions.length>0&&<section className="card group-questions"><h2>Answer membership questions</h2>{group.approval_questions.map((question,index)=><label key={index}>{question}<textarea value={joinAnswers[index]||""} onChange={e=>setJoinAnswers(joinAnswers.map((x,i)=>i===index?e.target.value:x))}/></label>)}</section>}{group.join_requests?.length>0&&<section className="card group-requests"><h2>Membership requests</h2>{group.join_requests.map(request=><div className="group-request" key={request.id}><Avatar user={request.user}/><div><b>{request.user.name}</b>{request.answers.map((answer,index)=><small key={index}>{group.approval_questions[index]} — {answer}</small>)}</div><button className="primary" onClick={()=>review(request.id,"approve")}>Approve</button><button className="secondary" onClick={()=>review(request.id,"decline")}>Decline</button></div>)}</section>}

{group.pending_posts?.length>0&&<section className="card group-requests"><h2>Posts awaiting approval</h2>{group.pending_posts.map(item=><div className="group-request" key={item.id}><Avatar user={item.author}/><div><b>{item.author.name}</b><small>{item.content||"Media post"}</small></div><button className="primary" onClick={async()=>{await api(`/api/groups/${group.id}/posts/${item.id}/moderate/approve`,{method:"POST"});loadGroup()}}>Approve</button><button className="secondary" onClick={async()=>{await api(`/api/groups/${group.id}/posts/${item.id}/moderate/decline`,{method:"POST"});loadGroup()}}>Decline</button></div>)}</section>}{group.open_reports?.length>0&&<section className="card group-requests"><h2>Member reports</h2>{group.open_reports.map(report=><div className="group-request" key={report.id}><div><b>{report.reporter.name}</b><small>{report.reason} · Post #{report.post_id}</small></div><button className="secondary" onClick={async()=>{await api(`/api/groups/${group.id}/reports/${report.id}/resolve`,{method:"POST"});loadGroup()}}>Mark resolved</button></div>)}</section>}
{addMemberOpen&&<div className="modal-backdrop" onMouseDown={()=>setAddMemberOpen(false)}><div className="card group-add-member" onMouseDown={e=>e.stopPropagation()}><div className="section-head"><div><h2>Add member</h2><p>Search by name or username.</p></div><button className="icon-btn" onClick={()=>setAddMemberOpen(false)}><X/></button></div><form className="group-add-search" onSubmit={e=>{e.preventDefault();searchPeople()}}><input autoFocus value={addMemberQuery} onChange={e=>setAddMemberQuery(e.target.value)} placeholder="Search people..."/><button className="primary"><Search size={18}/> Search</button></form><div className="group-add-results">{addMemberResults.map(item=><div key={item.id}><Avatar user={item}/><span><b>{item.name}</b><small>@{item.username}</small></span><button className="primary" onClick={()=>addMember(item)}>Add</button></div>)}{addMemberQuery&&addMemberResults.length===0&&<p className="muted">No users found or everyone is already a member.</p>}</div></div></div>}
{tab==="about"&&<section className="card group-about"><div className="section-head"><h2>About this group</h2>{group.membership_status==="member"&&<button className="secondary" onClick={async()=>{await api(`/api/groups/${group.id}/notifications?enabled=${!group.notifications_enabled}`,{method:"POST"});loadGroup()}}>{group.notifications_enabled?"Turn off notifications":"Turn on notifications"}</button>}</div>
<h3>Purpose</h3><p>{group.description||"No description has been added."}</p><div className="group-facts"><span>{group.privacy==="private"?"🔒 Private":"🌐 Public"}</span><span>{group.visibility==="hidden"?"🙈 Hidden":"👁 Visible"}</span><span>👥 {group.member_count} members</span></div><h3>Group rules</h3><div className="group-rules">{group.rules?group.rules.split("\n").filter(Boolean).map((rule,index)=><div key={index}><b>{index+1}</b><span>{rule}</span></div>):<p>No group rules have been added.</p>}</div>{group.members&&<><h3>Admins and moderators</h3><div className="group-people-grid">{group.members.filter(item=>item.role!=="member").map(item=><div className="group-person" key={item.id}><Avatar user={item}/><span><b>{item.name}</b><small>{item.role}</small></span></div>)}</div></>}</section>}{tab==="discussion"&&(group.can_view_content?<><form className="card group-composer" onSubmit={publish}><h2>Create group post</h2><textarea value={post.content} onChange={e=>setPost({...post,content:e.target.value})} placeholder="Write something to the group..."/>{mediaFile&&<div className="file-chip">{mediaFile.name}</div>}<div><span className="group-compose-options">{group.allow_anonymous_posts&&<label><input type="checkbox" checked={post.is_anonymous} onChange={e=>setPost({...post,is_anonymous:e.target.checked})}/> Post anonymously</label>}<label className="secondary group-attach"><Paperclip size={17}/> Attach media/file<input hidden type="file" onChange={e=>setMediaFile(e.target.files?.[0]||null)}/></label></span><button className="primary">Post</button></div></form><section className="group-feed">{posts.length?posts.map(postCard):<div className="card empty">No group posts yet.</div>}</section></>:<div className="card empty"><h2>This is a private group</h2><p>Join the group to see its posts.</p></div>)}{tab==="featured"&&(group.can_view_content?<section className="group-feed">{posts.some(item=>item.is_pinned)?posts.filter(item=>item.is_pinned).map(postCard):<div className="card empty">No featured posts yet.</div>}</section>:<div className="card empty">Join the group to see featured posts.</div>)}{tab==="people"&&(group.membership_status==="member"?<section className="card group-people"><div className="section-head"><div><h2>People</h2><p>{group.member_count} members</p></div><div className="group-people-tools"><div className="group-member-search"><Search size={18}/><input value={memberQuery} onChange={e=>setMemberQuery(e.target.value)} placeholder="Search members..."/></div>{group.my_role==="admin"&&<button className="primary" onClick={()=>setAddMemberOpen(true)}><UserPlus size={18}/> Add member</button>}</div></div><div className="group-people-grid">
{filteredMembers.map(item=><div className="group-person" key={item.id}><Avatar user={item}/><span><b>{item.name}</b><small>@{item.username} · {item.role}{item.posting_muted_until&&` · muted until ${formatDateTime(item.posting_muted_until)}`}</small></span>{group.my_role==="admin"&&item.id!==group.owner.id&&<div className="group-member-menu-wrap"><button className="icon-btn" onClick={()=>setMemberMenu(memberMenu===item.id?null:item.id)}><MoreHorizontal/></button>{memberMenu===item.id&&<div className="group-member-menu"><button onClick={()=>memberAction(item,"role:admin")}>Make admin</button><button onClick={()=>memberAction(item,"role:moderator")}>Make moderator</button><button onClick={()=>memberAction(item,"role:member")}>Make member</button><button onClick={()=>memberAction(item,"mute_day")}>Mute posting · 24 hours</button><button onClick={()=>memberAction(item,"mute_week")}>Mute posting · 7 days</button>{item.posting_muted_until&&<button onClick={()=>memberAction(item,"unmute")}>Restore posting</button>}<button className="danger-link" onClick={()=>memberAction(item,"kick")}>Remove from group</button><button className="danger-link" onClick={()=>memberAction(item,"ban")}>Ban permanently</button></div>}</div>}</div>)}
</div></section>:<div className="card empty">Join the group to see members.</div>)}{tab==="media"&&(group.can_view_content?<section className="card group-library"><h2>Photos and videos</h2><div className="group-media-grid">{mediaPosts.map(item=>item.media_type==="video"?<video key={item.id} src={asset(item.media_url)} controls/>:<img key={item.id} src={asset(item.media_url)}/>)}{!mediaPosts.length&&<p>No photos or videos yet.</p>}</div></section>:<div className="card empty">Join the group to see media.</div>)}{tab==="files"&&(group.can_view_content?<section className="card group-library"><h2>Files</h2><div className="group-file-list">{filePosts.map(item=><a key={item.id} href={asset(item.media_url)} target="_blank" rel="noreferrer"><FileText/><span><b>{item.content||"Attached file"}</b><small>{formatDateTime(item.created_at)}</small></span><Download/></a>)}{!filePosts.length&&<p>No files have been shared.</p>}</div></section>:<div className="card empty">Join the group to see files.</div>)}</div>;
}

const RESERVED_PATHS=new Set(["settings","friends","messages","notifications","activity-log","groups"]);
const currentPath=pathname=>decodeURIComponent(pathname.replace(/^\/+|\/+$/g,""));

function RoutedApp(){
  const navigate=useNavigate(),location=useLocation(),queryCache=useQueryClient();
  const[user,setUser]=useState(null),[view,setView]=useState("home"),[feed,setFeed]=useState([]),[profile,setProfile]=useState(null),[friends,setFriends]=useState([]),[requests,setRequests]=useState([]),[sentRequests,setSentRequests]=useState([]),[suggestions,setSuggestions]=useState([]),[target,setTarget]=useState(null),[conversations,setConversations]=useState([]),[notifs,setNotifs]=useState([]),[unread,setUnread]=useState(0),[messageUnread,setMessageUnread]=useState(0),[drop,setDrop]=useState(false),[accountDrop,setAccountDrop]=useState(false),[search,setSearch]=useState(""),[results,setResults]=useState([]),[routeError,setRouteError]=useState(""),[groupId,setGroupId]=useState(null),[newGroupChatOpen,setNewGroupChatOpen]=useState(false),[draftGroupChat,setDraftGroupChat]=useState(null);
  const[theme,setTheme]=useState(()=>localStorage.getItem("socialn_theme")||"dark");
  const[language,setLanguage]=useState(()=>localStorage.getItem("socialn_language")||"vi");
  const[timezone,setTimezone]=useState(()=>localStorage.getItem("socialn_timezone")||"auto");
  const[sidebarCollapsed,setSidebarCollapsed]=useState(()=>localStorage.getItem("socialn_sidebar_collapsed")==="true"),[mobileSidebarOpen,setMobileSidebarOpen]=useState(false);
  const[notificationPrefs,setNotificationPrefs]=useNotificationPreferences(),[messageToasts,setMessageToasts]=useState([]),[activityToasts,setActivityToasts]=useState([]);
  const[feedMeta,setFeedMeta]=useState({nextCursor:null,hasMore:true,groups:[]}),[feedLoading,setFeedLoading]=useState(false);
  const searchTimerRef=useRef(null);
  const feedSentinelRef=useRef(null),feedLoadingRef=useRef(false);
  const notificationPrefsRef=useRef(notificationPrefs),viewRef=useRef(view),targetRef=useRef(target),seenMessageNotificationsRef=useRef(new Set()),knownNotificationIdsRef=useRef(new Set()),notificationBaselineReadyRef=useRef(false);

  useEffect(()=>{document.documentElement.dataset.theme=theme;document.documentElement.style.colorScheme=theme;localStorage.setItem("socialn_theme",theme)},[theme]);
  useEffect(()=>{setSiteLanguage(language)},[language]);
  useEffect(()=>{localStorage.setItem("socialn_timezone",timezone)},[timezone]);
  useEffect(()=>{localStorage.setItem("socialn_sidebar_collapsed",String(sidebarCollapsed))},[sidebarCollapsed]);
  useEffect(()=>{notificationPrefsRef.current=notificationPrefs;localStorage.setItem("socialn_message_notifications",JSON.stringify(notificationPrefs))},[notificationPrefs]);
  useEffect(()=>{viewRef.current=view},[view]);
  useEffect(()=>{targetRef.current=target},[target]);
  function changeTimezone(value){localStorage.setItem("socialn_timezone",value);setTimezone(value)}

  function setRoute(path,nextView,{replace=false}={}){
    const normalized=path.startsWith("/")?path:`/${path}`;
    if(location.pathname!==normalized)navigate(normalized,{replace});
    setView(nextView);setDrop(false);setAccountDrop(false);setRouteError("");
    setMobileSidebarOpen(false);
  }

  async function loadFeed({reset=true}={}){if(feedLoadingRef.current)return;feedLoadingRef.current=true;setFeedLoading(true);try{const cursor=reset?null:feedMeta.nextCursor;if(!reset&&!cursor)return;const data=await api(`/api/posts/feed?limit=12${cursor?`&cursor=${encodeURIComponent(cursor)}`:""}`),rows=Array.isArray(data.items)?data.items:[];setFeed(current=>reset?rows:[...current,...rows.filter(row=>!current.some(item=>item.id===row.id))]);setFeedMeta({nextCursor:data.next_cursor||null,hasMore:Boolean(data.has_more),groups:data.suggested_groups||[]})}catch(e){console.error(e);if(reset)setFeed([])}finally{feedLoadingRef.current=false;setFeedLoading(false)}}
  async function loadC(){try{const rows=await queryCache.fetchQuery({queryKey:["conversations"],queryFn:()=>api("/api/chat/conversations"),staleTime:0});setConversations((Array.isArray(rows)?rows:[]).filter(c=>c?.is_group||c?.user?.id))}catch(e){console.error(e);setConversations([])}}
  async function loadN({push=false}={}){try{const d=await queryCache.fetchQuery({queryKey:["notifications"],queryFn:()=>api("/api/notifications"),staleTime:0}),items=d.items||[],fresh=push&&notificationBaselineReadyRef.current?items.filter(item=>!item.is_read&&!knownNotificationIdsRef.current.has(item.id)&&!["new_message","group_mention"].includes(item.type)):[];items.forEach(item=>knownNotificationIdsRef.current.add(item.id));notificationBaselineReadyRef.current=true;setNotifs(items);setUnread(d.unread_count||0);fresh.slice().reverse().forEach(handleActivityNotification);return d}catch(e){console.error(e);return null}}
  async function loadMessageUnread(){try{const d=await api("/api/chat/unread-count");setMessageUnread(d.unread_count||0)}catch(e){console.error(e)}}
  async function refresh(){loadFeed();loadN();loadC();loadMessageUnread();try{const [f,r,sent,s]=await Promise.all([api("/api/friends"),api("/api/friends/requests"),api("/api/friends/requests/sent"),api("/api/users/suggestions/people")]);setFriends(f);setRequests(r);setSentRequests(sent);setSuggestions(s)}catch(e){console.error(e)}}

  useEffect(()=>{if(view!=="home"||!feedMeta.hasMore||!feedSentinelRef.current)return;const observer=new IntersectionObserver(entries=>{if(entries[0]?.isIntersecting)loadFeed({reset:false})},{rootMargin:"500px 0px"});observer.observe(feedSentinelRef.current);return()=>observer.disconnect()},[view,feedMeta.nextCursor,feedMeta.hasMore]);

  async function openProfile(id,{replace=false}={}){
    try{const d=await api(`/api/users/${id}/profile`);setProfile(d);setRoute(`/${encodeURIComponent(d.user.username)}`,"profile",{replace})}catch(e){setRouteError(e.message)}
  }
  async function openUsername(username,{replace=false}={}){
    try{const d=await api(`/api/users/username/${encodeURIComponent(username)}/profile`);setProfile(d);setRoute(`/${encodeURIComponent(d.user.username)}`,"profile",{replace})}catch(e){setView("not_found");setRouteError(e.message)}
  }
  async function reloadProfile(id){try{const d=await api(`/api/users/${id}/profile`);setProfile(d);setView("profile");refresh()}catch(e){setRouteError(e.message)}}
  function go(path,nextView){setRoute(path,nextView)}
  function message(u){setTarget(u);setRoute(`/messages/${encodeURIComponent(u.username)}`,"chat");loadC()}
  function openGroupChat(c){setTarget({...c,id:c.group_chat_id,is_group:true});setRoute(`/messages/group/${c.group_chat_id}`,"chat");loadC()}

  async function openMessageNotification(item){
    setMessageToasts(rows=>rows.filter(row=>row.toastId!==item.toastId));
    if(item.is_group){try{const d=await api(`/api/chat/group-conversations/${item.group_chat_id}/messages`);setTarget({...d.group,id:d.group.id,group_chat_id:d.group.id,is_group:true});setRoute(`/messages/group/${item.group_chat_id}`,"chat")}catch(e){setRouteError(e.message)}}
    else if(item.actor)message(item.actor);
  }
  function playMessageNotificationSound(){
    try{const AudioContext=window.AudioContext||window.webkitAudioContext;if(!AudioContext)return;const context=new AudioContext(),oscillator=context.createOscillator(),gain=context.createGain();oscillator.type="sine";oscillator.frequency.setValueAtTime(740,context.currentTime);oscillator.frequency.exponentialRampToValueAtTime(980,context.currentTime+.12);gain.gain.setValueAtTime(.0001,context.currentTime);gain.gain.exponentialRampToValueAtTime(.11,context.currentTime+.015);gain.gain.exponentialRampToValueAtTime(.0001,context.currentTime+.22);oscillator.connect(gain);gain.connect(context.destination);oscillator.start();oscillator.stop(context.currentTime+.23);oscillator.onended=()=>context.close()}catch{}
  }
  function handleMessageNotification(payload){
    if(payload?.type!=="message_notification"||payload.silent)return;
    const prefs=notificationPrefsRef.current;
    if(!prefs.enabled)return;
    const id=String(payload.message_id||`${payload.conversation_id}-${payload.created_at}`);
    if(seenMessageNotificationsRef.current.has(id))return;
    seenMessageNotificationsRef.current.add(id);
    if(seenMessageNotificationsRef.current.size>300)seenMessageNotificationsRef.current=new Set([id]);
    const current=targetRef.current;
    const alreadyOpen=viewRef.current==="chat"&&(payload.is_group?current?.is_group&&Number(current.group_chat_id)===Number(payload.group_chat_id):!current?.is_group&&Number(current?.id)===Number(payload.actor?.id));
    if(alreadyOpen&&document.visibilityState==="visible")return;
    const displayPreview=prefs.preview==="hidden"?"You have a new message":prefs.preview==="sender"?"New message":payload.preview||"New message";
    const item={...payload,kind:"message",displayPreview,duration:Number(prefs.duration)||6000,toastId:`message-${id}`};
    if(prefs.sound)playMessageNotificationSound();
    if(document.visibilityState==="visible"){
      setMessageToasts(rows=>[item,...rows.filter(row=>row.toastId!==item.toastId)].slice(0,4));
      window.setTimeout(()=>setMessageToasts(rows=>rows.filter(row=>row.toastId!==item.toastId)),item.duration);
    }else if(prefs.desktop&&"Notification" in window&&Notification.permission==="granted"){
      const title=prefs.preview==="hidden"?"SocialN":payload.is_group?payload.conversation_name:payload.actor?.name||"SocialN";
      const nativeNotification=new Notification(title,{body:displayPreview,icon:asset(payload.conversation_avatar_url)||undefined,tag:`socialn-${payload.is_group?"group":"direct"}-${payload.group_chat_id||payload.actor?.id}`,silent:true});
      nativeNotification.onclick=()=>{window.focus();nativeNotification.close();openMessageNotification(item)};
    }
  }
  function handleActivityNotification(notification){
    const prefs=notificationPrefsRef.current;if(!prefs.enabled)return;
    const labels={friend_request:"FRIEND REQUEST",friend_accept:"NEW FRIEND",post_comment:"NEW COMMENT",post_reaction:"NEW REACTION",post_share:"POST SHARED",message_reaction:"MESSAGE REACTION",relationship_request:"RELATIONSHIP REQUEST",relationship_accepted:"RELATIONSHIP UPDATE",relationship_declined:"RELATIONSHIP UPDATE",group_welcome:"GROUP UPDATE"};
    const displayMessage=prefs.preview==="hidden"?"You have a new notification":prefs.preview==="sender"?"New activity on SocialN":notification.message;
    const item={...notification,notification,kind:"activity",categoryLabel:labels[notification.type]||"SOCIALN UPDATE",displayMessage,duration:Number(prefs.duration)||6000,toastId:`activity-${notification.id}`};
    if(prefs.sound)playMessageNotificationSound();
    if(document.visibilityState==="visible"){
      setActivityToasts(rows=>[item,...rows.filter(row=>row.toastId!==item.toastId)].slice(0,4));
      window.setTimeout(()=>setActivityToasts(rows=>rows.filter(row=>row.toastId!==item.toastId)),item.duration);
    }else if(prefs.desktop&&"Notification" in window&&Notification.permission==="granted"){
      const title=prefs.preview==="hidden"?"SocialN":notification.actor?.name||labels[notification.type]||"SocialN";
      const nativeNotification=new Notification(title,{body:displayMessage,icon:asset(notification.actor?.avatar_url)||undefined,tag:`socialn-notification-${notification.id}`,silent:true});
      nativeNotification.onclick=()=>{window.focus();nativeNotification.close();openActivityNotification(item)};
    }
  }
  function openActivityNotification(item){setActivityToasts(rows=>rows.filter(row=>row.toastId!==item.toastId));read(item.notification)}

  async function resolvePath(replace=false){
    const path=currentPath(location.pathname);
    if(!path){setRoute("/","home",{replace});return}
    const [head,second,third]=path.split("/");
    if(head==="settings"){setView("settings");return}
    if(head==="friends"){setView("friends");return}
    if(head==="notifications"){setView("notifications");return}
    if(head==="activity-log"){setView("activity");return}
    if(head==="groups"){setGroupId(second?Number(second):null);setView("groups");return}
    if(head==="messages"){
      setView("chat");
      if(second==="invite"&&third){try{const joined=await api(`/api/chat/group-invites/${encodeURIComponent(third)}`,{method:"POST"});if(joined.status==="pending"){setTarget(null);setRouteError("Your request was sent to the group admins for approval.")}else{const d=await api(`/api/chat/group-conversations/${joined.group_id}/messages`);setTarget({...d.group,id:d.group.id,group_chat_id:d.group.id,is_group:true});setRoute(`/messages/group/${joined.group_id}`,"chat",{replace:true})}}catch(e){setRouteError(e.message)}}
      else if(second==="group"&&third){try{const d=await api(`/api/chat/group-conversations/${Number(third)}/messages`);setTarget({...d.group,id:d.group.id,group_chat_id:d.group.id,is_group:true})}catch(e){setRouteError(e.message)}}
      else if(second&&second!=="new-group"){try{const d=await api(`/api/users/username/${encodeURIComponent(second)}/profile`);setTarget(d.user)}catch(e){setRouteError(e.message)}}
      else if(!second)setTarget(null);
      return;
    }
    if(!RESERVED_PATHS.has(head))await openUsername(head,{replace:true});
  }

  useEffect(()=>{let live=true;authService.restore().then(()=>api("/api/users/me")).then(current=>{if(live)setUser(current)}).catch(()=>{authService.clear();if(live&&location.pathname!=="/")navigate("/",{replace:true})});return()=>{live=false}},[]);
  useEffect(()=>{if(!user)return;resolvePath(true)},[user?.id,location.pathname]);
  useEffect(()=>{if(!user)return;let w=null,heartbeat=null,cancelled=false;refresh();loadN().then(()=>{if(cancelled)return;w=createAuthenticatedSocket("/api/notifications/ws");w.onopen=()=>{w.send("ready");heartbeat=window.setInterval(()=>{if(w?.readyState===WebSocket.OPEN)w.send("ping")},45000)};w.onmessage=async event=>{loadMessageUnread();loadC();try{const payload=JSON.parse(event.data);handleMessageNotification(payload);await loadN({push:payload?.type!=="message_notification"});if(["relationship_accepted","relationship_declined","relationship_unlinked"].includes(payload?.reason)){const updated=await api(`/api/users/${user.id}/profile`);setProfile(current=>Number(current?.user?.id)===Number(user.id)?updated:current);setUser(await api("/api/users/me"))}}catch{await loadN({push:true})}}});return()=>{cancelled=true;if(heartbeat)window.clearInterval(heartbeat);w?.close()}},[user?.id]);

  function query(v){setSearch(v);clearTimeout(searchTimerRef.current);if(!v.trim()){setResults([]);return}searchTimerRef.current=setTimeout(async()=>{try{setResults(await api(`/api/users/search?q=${encodeURIComponent(v.trim())}`))}catch{setResults([])}},450)}
  async function read(n){if(!n.is_read)await api(`/api/notifications/${n.id}/read`,{method:"POST"});if(n.entity_type==="group"&&n.entity_id){setGroupId(n.entity_id);go(`/groups/${n.entity_id}`,"groups")}else if(n.entity_type==="chat_group"&&n.entity_id){try{const d=await api(`/api/chat/group-conversations/${n.entity_id}/messages`);setTarget({...d.group,id:d.group.id,group_chat_id:d.group.id,is_group:true});go(`/messages/group/${n.entity_id}`,"chat")}catch(e){setRouteError(e.message)}}else if(["new_message","message_reaction"].includes(n.type)&&n.actor)message(n.actor);else if(n.type==="friend_request")go("/friends","friends");else if(n.entity_type==="post"&&n.entity_id){go("/","home");await loadFeed();window.setTimeout(()=>document.getElementById(`post-${n.entity_id}`)?.scrollIntoView({behavior:"smooth",block:"center"}),120)}else if(n.actor)openProfile(n.actor.id);setDrop(false);loadN()}
  async function respondRelationship(n,action){try{await api(`/api/users/relationship-requests/${n.entity_id}/${action}`,{method:"POST"});await loadN();const updated=await api("/api/users/me");setUser(updated);if(view==="profile"&&Number(profile?.user?.id)===Number(user.id))await reloadProfile(user.id)}catch(e){alert(e.message)}}
  async function logout(){try{await api("/api/auth/logout",{method:"POST",authRetry:false})}catch{}authService.clear();queryCache.clear();navigate("/",{replace:true});setUser(null)}
  function toggleSidebar(){if(window.matchMedia("(max-width: 900px)").matches)setMobileSidebarOpen(value=>!value);else setSidebarCollapsed(value=>!value)}

  if(!user)return <Login language={language} onLanguageChange={setLanguage} theme={theme} onThemeChange={setTheme} onLogin={u=>{setUser(u);queryCache.setQueryData(["session"],u);navigate("/",{replace:true})}}/>;
  return <div><ConfirmHost/><MetroMessageToasts items={[...messageToasts,...activityToasts].slice(0,4)} onOpen={item=>item.kind==="activity"?openActivityNotification(item):openMessageNotification(item)} onDismiss={id=>{setMessageToasts(rows=>rows.filter(row=>row.toastId!==id));setActivityToasts(rows=>rows.filter(row=>row.toastId!==id))}}/>
    <header className="topbar"><button className="sidebar-toggle" onClick={toggleSidebar} aria-label={mobileSidebarOpen||!sidebarCollapsed?"Close navigation menu":"Open navigation menu"} aria-expanded={mobileSidebarOpen||!sidebarCollapsed}><Menu size={23}/></button><div className="brand" onClick={()=>go("/","home")}>Social<span>N</span></div><div className="search"><Search/><input value={search} onChange={e=>query(e.target.value)} placeholder="Search SocialN..."/>{results.length>0&&<div className="search-results">{results.map(u=><button key={u.id} onClick={()=>{openProfile(u.id);setResults([]);setSearch("")}}><Avatar user={u}/><span>{u.name}<small>@{u.username}</small></span></button>)}</div>}</div>
      <div className="top-actions">
        <button className="message-icon-btn top-messages" title="Messages" onClick={()=>{setTarget(null);go("/messages","chat")}}><MessageCircle/>{messageUnread>0&&<span className="badge">{messageUnread>99?"99+":messageUnread}</span>}</button>
        <div className="notif-wrap top-notifications"><button className="notification-btn" title="Notifications" onClick={()=>{setDrop(value=>!value);setAccountDrop(false)}}><Bell/>{unread>0&&<span className="badge">{unread}</span>}</button>{drop&&<div className="notif-dropdown"><div className="notif-dropdown-head"><b>Notifications</b><button onClick={async()=>{await api("/api/notifications/read-all",{method:"POST"});loadN()}}>Mark all read</button></div><div className="notif-scroll">{notifs.slice(0,20).map(n=>n.type==="relationship_request"?<div className={`notification-row relationship-notification ${n.is_read?"":"unread"}`} key={n.id}><Avatar user={n.actor}/><div className="notification-content">{n.message}<small>{formatDateTime(n.created_at)}</small><div className="relationship-notification-actions"><button className="primary" onClick={()=>respondRelationship(n,"accept")}>Accept</button><button className="secondary" onClick={()=>respondRelationship(n,"decline")}>Decline</button></div></div></div>:<button className={`notification-row ${n.is_read?"":"unread"}`} key={n.id} onClick={()=>read(n)}><Avatar user={n.actor}/><div className="notification-content">{n.message}<small>{formatDateTime(n.created_at)}</small></div></button>)}</div></div>}</div>
        <div className="account-wrap"><button className="account-trigger" title="Account" aria-expanded={accountDrop} onClick={()=>{setAccountDrop(value=>!value);setDrop(false)}}><Avatar user={user} size={40}/><span className="account-caret">⌄</span></button>{accountDrop&&<div className="account-dropdown"><button className="account-profile" onClick={()=>openProfile(user.id)}><Avatar user={user} size={46}/><span><b>{user.name}</b><small>View your profile</small></span></button><div className="account-divider"/><button onClick={()=>go("/settings","settings")}><Settings size={20}/><span>Settings</span></button><button onClick={logout}><LogOut size={20}/><span>Log out</span></button></div>}</div>
      </div>
    </header>
    <div className={`layout ${sidebarCollapsed?"sidebar-collapsed":""}`}>{mobileSidebarOpen&&<button className="sidebar-backdrop" aria-label="Close navigation menu" onClick={()=>setMobileSidebarOpen(false)}/>}<aside className={`sidebar ${mobileSidebarOpen?"open":""}`}><button className="side-user" title={user.name} onClick={()=>openProfile(user.id)}><Avatar user={user}/><b className="sidebar-label">{user.name}</b></button><button className={view==="home"?"selected":""} title="Home" onClick={()=>go("/","home")}><Home/><span className="sidebar-label">Home</span></button><button className={view==="friends"?"selected":""} title="Friends" onClick={()=>go("/friends","friends")}><UserCheck/><span className="sidebar-label">Friends</span>{requests.length>0&&<span className="side-badge">{requests.length}</span>}</button><button className={view==="groups"?"selected":""} title="Groups" onClick={()=>{setGroupId(null);go("/groups","groups")}}><UsersRound/><span className="sidebar-label">Groups</span></button><button className={view==="chat"?"selected":""} title="Messages" onClick={()=>{setTarget(null);go("/messages","chat")}}><MessageCircle/><span className="sidebar-label">Messages</span></button><button className={view==="activity"?"selected":""} title="Activity log" onClick={()=>go("/activity-log","activity")}><History/><span className="sidebar-label">Activity log</span></button><button className={view==="settings"?"selected":""} title="Settings" onClick={()=>go("/settings","settings")}><Settings/><span className="sidebar-label">Settings</span></button></aside>
      <main className={`main ${view==="chat"?"chat-main":view==="profile"?"profile-main":["home","friends","settings","activity","notifications","groups"].includes(view)?"adaptive-main":""}`}>
        {routeError&&<div className="error">{routeError}</div>}
        {view==="home"&&<FeedPage composer={<PostComposer onCreated={p=>setFeed(v=>[p,...v])}/>} posts={feed.map(p=><PostCard key={p.id} post={p} me={user} onOpenProfile={openProfile} onUpdated={updated=>setFeed(v=>v.map(x=>x.id===updated.id?updated:x))} onDeleted={id=>setFeed(v=>v.filter(x=>x.id!==id))} onHidden={id=>setFeed(v=>v.filter(x=>x.id!==id))} onShared={shared=>setFeed(v=>[shared,...v])}/>)} empty={<div className="card empty">No posts yet. Create the first post.</div>} suggestedGroups={feedMeta.groups} onOpenGroup={id=>{setGroupId(id);go(`/groups/${id}`,"groups")}} footer={<div ref={feedSentinelRef} className="feed-load-more">{feedLoading?"Loading more posts…":feedMeta.hasMore?<button className="secondary" onClick={()=>loadFeed({reset:false})}>Load more</button>:feed.length?"You're all caught up":""}</div>}
        />}
        {view==="profile"&&profile&&<ProfilePage><Profile data={profile} me={user} reload={reloadProfile} message={message} open={openProfile}/></ProfilePage>}
        {view==="friends"&&<div className="friends-page"><div className="card friends-section"><div className="section-head"><h2>Friend requests</h2>{requests.length>0&&<span className="count-chip">{requests.length}</span>}</div>{requests.length===0&&<div className="muted">No pending requests.</div>}{requests.map(r=><div className="request-row" key={r.id}><Avatar user={r.user} onClick={()=>openProfile(r.user.id)}/><button className="name-block" onClick={()=>openProfile(r.user.id)}><b>{r.user.name}</b></button><button className="primary" onClick={async()=>{await api(`/api/friends/${r.id}/accept`,{method:"POST"});refresh()}}>Confirm</button><button className="secondary" onClick={async()=>{await api(`/api/friends/${r.id}/reject`,{method:"POST"});refresh()}}>Delete</button></div>)}</div><div className="card friends-section"><div className="section-head"><div><h2>Sent requests</h2><p className="muted small">Manage friend requests you have sent.</p></div>{sentRequests.length>0&&<span className="count-chip">{sentRequests.length}</span>}</div>{sentRequests.length===0?<div className="muted sent-empty">No sent requests.</div>:<div className="request-list">{sentRequests.map(r=><div className="request-row sent-request-row" key={r.id}><Avatar user={r.user} onClick={()=>openProfile(r.user.id)}/><button className="name-block" onClick={()=>openProfile(r.user.id)}><b>{r.user.name}</b><small className="muted">Sent {formatDateTime(r.created_at)}</small></button><button className="secondary cancel-request" onClick={async()=>{if(await confirmDialog({variant:"confirm",title:"Cancel friend request?",message:`Withdraw the friend request sent to ${r.user.name}?`,confirmLabel:"Withdraw",cancelLabel:"Keep request"})){await api(`/api/friends/requests/${r.id}`,{method:"DELETE"});refresh()}}}>Withdraw</button></div>)}</div>}</div><div className="card friends-section"><h2>Your friends</h2><div className="people-grid">{friends.map(u=><div className="person" key={u.id}><Avatar user={u} onClick={()=>openProfile(u.id)}/><button className="name-link" onClick={()=>openProfile(u.id)}>{u.name}</button><button className="secondary" onClick={()=>message(u)}>Message</button></div>)}</div></div><div className="card friends-section"><h2>People you may know</h2><div className="people-grid">{suggestions.map(u=><div className="person" key={u.id}><Avatar user={u} onClick={()=>openProfile(u.id)}/><button className="name-link" onClick={()=>openProfile(u.id)}>{u.name}</button><small>{u.mutual_friends_count} mutual friends</small><button className="primary" onClick={async()=>{await api(`/api/friends/${u.id}`,{method:"POST"});refresh()}}>Add friend</button></div>)}</div></div></div>}
        {view==="chat"&&<MessagesPage hasSelection={Boolean(target)}><div className="conversation-list card"><div className="conversation-title"><span>Messages</span><button className="compose-message" title="Compose message" onClick={()=>setNewGroupChatOpen(true)}><Edit2 size={19}/></button></div>
          {conversations.filter(c=>!c.is_group&&Number(c.user.id)===Number(user.id)).map(c=><ConversationRow key={c.id} conversation={c} personalStorage active={!target?.is_group&&Number(target?.id)===Number(user.id)} onOpen={()=>message(user)} onChanged={loadC} onDeleted={()=>{setTarget(null);setRoute("/messages","chat")}}/>)}
          {!conversations.some(c=>!c.is_group&&Number(c.user.id)===Number(user.id))&&<button className="self-vault" onClick={()=>message(user)}><Avatar user={user}/><span><b>{user.name} (You)</b><small>Personal storage</small></span></button>}
          {draftGroupChat&&<ConversationRow conversation={draftGroupChat} active={target?.is_group_draft} onOpen={()=>{setTarget(draftGroupChat);setRoute("/messages/new-group","chat")}}/>}
          {conversations.filter(c=>c.is_group||Number(c.user?.id)!==Number(user.id)).map(c=>c.is_group
            ?<ConversationRow key={`group-${c.group_chat_id}`} conversation={c} active={target?.is_group&&Number(target?.group_chat_id)===Number(c.group_chat_id)} onOpen={()=>openGroupChat(c)} onChanged={loadC}/>
            :<ConversationRow key={c.id} conversation={c} active={!target?.is_group&&Number(target?.id)===Number(c.user.id)} onOpen={()=>message(c.user)} onChanged={loadC} onDeleted={row=>{if(Number(target?.id)===Number(row.user.id)){setTarget(null);setRoute("/messages","chat")}}}/>)}
        </div><Chat me={user} target={target} open={openProfile} onMobileBack={()=>{setTarget(null);setRoute("/messages","chat")}} onChanged={()=>{loadC();loadMessageUnread()}} onGroupActivated={group=>{setDraftGroupChat(null);setTarget({...group,is_group:true});setRoute(`/messages/group/${group.group_chat_id}`,"chat");loadC()}}/>{newGroupChatOpen&&<NewGroupChatModal friends={friends} onClose={()=>setNewGroupChatOpen(false)} onCreate={draft=>{const item={...draft,id:"draft",group_chat_id:"draft",last_message:"Draft · Send a message to create",last_message_type:"text"};setDraftGroupChat(item);setTarget(item);setNewGroupChatOpen(false);setRoute("/messages/new-group","chat")}}/>}</MessagesPage>}
        {view==="notifications"&&<div className="card notifications-page">{notifs.map(n=><button className="notification-row" key={n.id} onClick={()=>read(n)}>{n.message}</button>)}</div>}
        {view==="activity"&&<ActivityLogPage openProfile={openProfile}/>} 
        {view==="groups"&&<GroupsModule><GroupsPage groupId={groupId} onOpen={id=>{setGroupId(id);go(`/groups/${id}`,"groups")}}/></GroupsModule>}
        {view==="settings"&&<SettingsModule><SettingsPage user={user} onUserUpdated={setUser} onAccountClosed={logout} openProfile={openProfile} openMessage={message} theme={theme} onThemeChange={setTheme} language={language} onLanguageChange={setLanguage} timezone={timezone} onTimezoneChange={changeTimezone} notificationPrefs={notificationPrefs} onNotificationPrefsChange={setNotificationPrefs}/></SettingsModule>}
        {view==="not_found"&&<div className="card empty"><h2>Page not found</h2><button className="primary" onClick={()=>go("/","home")}>Go home</button></div>}
      </main>
    </div>
    <nav className="mobile-bottom-nav" aria-label="Primary navigation">
      <button className={view==="home"?"active":""} onClick={()=>go("/","home")}><Home/><span>Home</span></button>
      <button className={view==="friends"?"active":""} onClick={()=>go("/friends","friends")}><UserCheck/>{requests.length>0&&<i>{requests.length>99?"99+":requests.length}</i>}<span>Friends</span></button>
      <button className={view==="groups"?"active":""} onClick={()=>{setGroupId(null);go("/groups","groups")}}><UsersRound/><span>Groups</span></button>
      <button className={view==="chat"?"active":""} onClick={()=>{setTarget(null);go("/messages","chat")}}><MessageCircle/>{messageUnread>0&&<i>{messageUnread>99?"99+":messageUnread}</i>}<span>Messages</span></button>
      <button onClick={()=>setMobileSidebarOpen(value=>!value)} aria-expanded={mobileSidebarOpen}><Menu/><span>Menu</span></button>
    </nav>
  </div>
}

createRoot(document.getElementById("root")).render(<ErrorBoundary><QueryClientProvider client={queryClient}><BrowserRouter><RoutedApp/></BrowserRouter></QueryClientProvider></ErrorBoundary>);
