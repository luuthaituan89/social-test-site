import json
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import Group, GroupBan, GroupJoinRequest, GroupMember, GroupPost, GroupPostComment, GroupPostHidden, GroupPostReaction, GroupReport, Post, Privacy, User
from ..schemas import GroupCommentCreate, GroupCoverUpdate, GroupCreate, GroupJoinIn, GroupPostCreate, GroupReportCreate, GroupUpdate, ReactionIn
from ..activity import log_activity
from ..notifications import create_notification
from .notifications import notification_ws

router = APIRouter(prefix="/api/groups", tags=["Groups"])
PRIVACY = {"public", "private"}
VISIBILITY = {"visible", "hidden"}
GROUP_TYPES = {"general", "social_learning", "buy_sell", "work_project"}
ROLES = {"admin", "moderator", "member"}
REACTIONS = {"like", "love", "haha", "wow", "sad", "angry"}


def user_payload(user: User):
    return {"id": user.id, "username": user.username, "name": user.name, "avatar_url": user.avatar_url}


def membership(db: Session, group_id: int, user_id: int):
    return db.query(GroupMember).filter(GroupMember.group_id == group_id, GroupMember.user_id == user_id).first()


def questions(group: Group):
    try:
        value = json.loads(group.approval_questions or "[]")
        return value if isinstance(value, list) else []
    except Exception:
        return []


def can_discover(group: Group, member: GroupMember | None):
    return group.visibility == "visible" or member is not None


def can_view_content(group: Group, member: GroupMember | None):
    return group.privacy == "public" or member is not None


def group_payload(db: Session, group: Group, viewer: User, detail=False):
    member = membership(db, group.id, viewer.id)
    pending = db.query(GroupJoinRequest).filter(GroupJoinRequest.group_id == group.id, GroupJoinRequest.user_id == viewer.id, GroupJoinRequest.status == "pending").first()
    count = db.query(GroupMember).filter(GroupMember.group_id == group.id).count()
    owner = db.get(User, group.owner_id)
    payload = {
        "id": group.id, "name": group.name, "description": group.description, "rules": group.rules,
        "privacy": group.privacy, "visibility": group.visibility, "group_type": group.group_type,
        "cover_url": group.cover_url, "approval_questions": questions(group), "created_at": group.created_at,
        "owner": user_payload(owner), "member_count": count, "my_role": member.role if member else None,
        "membership_status": "member" if member else "pending" if pending else "none",
        "can_view_content": can_view_content(group, member), "allow_anonymous_posts": group.allow_anonymous_posts,
        "require_post_approval": group.require_post_approval,
        "notifications_enabled": member.notifications_enabled if member else None,
    }
    if detail and member:
        rows = db.query(GroupMember).filter(GroupMember.group_id == group.id).order_by(GroupMember.joined_at.asc()).all()
        payload["members"] = [{**user_payload(db.get(User, row.user_id)), "role": row.role, "joined_at": row.joined_at, "posting_muted_until": row.posting_muted_until} for row in rows]
        if member.role in {"admin", "moderator"}:
            requests = db.query(GroupJoinRequest).filter(GroupJoinRequest.group_id == group.id, GroupJoinRequest.status == "pending").order_by(GroupJoinRequest.created_at.asc()).all()
            payload["join_requests"] = [{"id": row.id, "user": user_payload(db.get(User, row.user_id)), "answers": json.loads(row.answers or "[]"), "created_at": row.created_at} for row in requests]
            pending_posts=db.query(GroupPost).filter(GroupPost.group_id==group.id,GroupPost.status=="pending").order_by(GroupPost.created_at.asc()).all()
            payload["pending_posts"]=[{"id":row.id,"content":row.content,"media_url":row.media_url,"media_type":row.media_type,"created_at":row.created_at,"author":user_payload(db.get(User,row.author_id))} for row in pending_posts]
            reports=db.query(GroupReport).filter(GroupReport.group_id==group.id,GroupReport.status=="open").order_by(GroupReport.created_at.desc()).all()
            payload["open_reports"]=[{"id":row.id,"reason":row.reason,"post_id":row.post_id,"created_at":row.created_at,"reporter":user_payload(db.get(User,row.reporter_id))} for row in reports]
    return payload


@router.get("")
def list_groups(q: str = "", db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.query(Group).order_by(Group.created_at.desc()).limit(200).all()
    needle = q.strip().lower()
    visible = []
    for group in rows:
        member = membership(db, group.id, user.id)
        if not can_discover(group, member):
            continue
        if needle and needle not in group.name.lower() and needle not in (group.description or "").lower():
            continue
        visible.append(group_payload(db, group, user))
    return visible


@router.post("")
def create_group(data: GroupCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if data.privacy not in PRIVACY or data.visibility not in VISIBILITY or data.group_type not in GROUP_TYPES:
        raise HTTPException(400, "Invalid group settings")
    prompts = [item.strip() for item in data.approval_questions if item.strip()][:3]
    group = Group(owner_id=user.id, name=data.name.strip(), description=(data.description or "").strip() or None,
                  rules=(data.rules or "").strip() or None,
                  privacy=data.privacy, visibility=data.visibility, group_type=data.group_type,
                  cover_url=data.cover_url, approval_questions=json.dumps(prompts, ensure_ascii=False))
    db.add(group); db.flush()
    db.add(GroupMember(group_id=group.id, user_id=user.id, role="admin"))
    log_activity(db, user.id, "groups", "group_created", f"Created group {group.name}", entity_type="group", entity_id=group.id)
    db.commit(); db.refresh(group)
    return group_payload(db, group, user, True)


@router.get("/{group_id}")
def get_group(group_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    group = db.get(Group, group_id)
    if not group:
        raise HTTPException(404, "Group not found")
    return group_payload(db, group, user, True)


@router.post("/{group_id}/join")
async def join_group(group_id: int, data: GroupJoinIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    group = db.get(Group, group_id)
    if not group:
        raise HTTPException(404, "Group not found")
    if membership(db, group_id, user.id):
        raise HTTPException(400, "You are already a member")
    if db.query(GroupBan).filter(GroupBan.group_id == group_id, GroupBan.user_id == user.id).first():
        raise HTTPException(403, "You have been banned from this group")
    prompts = questions(group)
    answers = [item.strip() for item in data.answers]
    if prompts and (len(answers) < len(prompts) or any(not answers[index] for index in range(len(prompts)))):
        raise HTTPException(400, "Please answer all membership questions")
    existing = db.query(GroupJoinRequest).filter(GroupJoinRequest.group_id == group_id, GroupJoinRequest.user_id == user.id).first()
    if group.privacy == "public" and not prompts:
        db.add(GroupMember(group_id=group_id, user_id=user.id, role="member"))
        if existing: db.delete(existing)
        create_notification(db, user_id=user.id, actor_id=None, type="group_welcome",
                            message=f"Welcome to {group.name}", entity_type="group", entity_id=group.id)
        result = "joined"
    else:
        if existing:
            existing.answers = json.dumps(answers, ensure_ascii=False); existing.status = "pending"; existing.created_at = datetime.utcnow(); existing.responded_at = None
        else:
            db.add(GroupJoinRequest(group_id=group_id, user_id=user.id, answers=json.dumps(answers, ensure_ascii=False)))
        result = "pending"
    db.commit()
    if result == "joined":
        await notification_ws.send(user.id, {"type": "notification_refresh", "reason": "group_joined", "group_id": group.id})
    return {"status": result}


@router.delete("/{group_id}/membership")
def leave_group(group_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    group = db.get(Group, group_id)
    row = membership(db, group_id, user.id)
    if not group:
        raise HTTPException(404, "Group not found")
    if row and row.role == "admin" and db.query(GroupMember).filter(GroupMember.group_id == group_id, GroupMember.role == "admin").count() == 1:
        raise HTTPException(400, "Assign another admin before leaving")
    if row: db.delete(row)
    request = db.query(GroupJoinRequest).filter(GroupJoinRequest.group_id == group_id, GroupJoinRequest.user_id == user.id, GroupJoinRequest.status == "pending").first()
    if request: db.delete(request)
    db.commit()
    return {"message": "Membership removed"}


@router.post("/{group_id}/requests/{request_id}/{action}")
async def review_request(group_id: int, request_id: int, action: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    actor = membership(db, group_id, user.id)
    request = db.get(GroupJoinRequest, request_id)
    if not actor or actor.role not in {"admin", "moderator"}:
        raise HTTPException(403, "Admin or moderator access required")
    if not request or request.group_id != group_id or request.status != "pending" or action not in {"approve", "decline"}:
        raise HTTPException(404, "Join request not found")
    request.status = "approved" if action == "approve" else "declined"; request.responded_at = datetime.utcnow()
    if action == "approve" and not membership(db, group_id, request.user_id):
        db.add(GroupMember(group_id=group_id, user_id=request.user_id, role="member"))
        group = db.get(Group, group_id)
        create_notification(db, user_id=request.user_id, actor_id=user.id, type="group_welcome",
                            message=f"Welcome to {group.name}", entity_type="group", entity_id=group.id)
    db.commit()
    if action == "approve":
        await notification_ws.send(request.user_id, {"type": "notification_refresh", "reason": "group_joined", "group_id": group_id})
    return {"status": request.status}


@router.put("/{group_id}/members/{member_id}/role")
def change_role(group_id: int, member_id: int, role: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    actor = membership(db, group_id, user.id); target = membership(db, group_id, member_id)
    if not actor or actor.role != "admin": raise HTTPException(403, "Admin access required")
    group=db.get(Group,group_id)
    if not target or role not in ROLES: raise HTTPException(400, "Invalid member or role")
    if member_id==group.owner_id: raise HTTPException(400,"The group owner role cannot be changed")
    target.role = role; db.commit()
    return {"role": role}


@router.post("/{group_id}/members/{member_id}")
async def add_member(group_id: int, member_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    actor=membership(db,group_id,user.id);group=db.get(Group,group_id);target=db.get(User,member_id)
    if not group or not target: raise HTTPException(404,"Group or user not found")
    if not actor or actor.role!="admin": raise HTTPException(403,"Admin access required")
    if membership(db,group_id,member_id): raise HTTPException(400,"This user is already a member")
    if db.query(GroupBan).filter(GroupBan.group_id==group_id,GroupBan.user_id==member_id).first(): raise HTTPException(400,"This user is banned from the group")
    pending=db.query(GroupJoinRequest).filter(GroupJoinRequest.group_id==group_id,GroupJoinRequest.user_id==member_id,GroupJoinRequest.status=="pending").first()
    if pending: pending.status="approved";pending.responded_at=datetime.utcnow()
    db.add(GroupMember(group_id=group_id,user_id=member_id,role="member"))
    create_notification(db,user_id=member_id,actor_id=user.id,type="group_welcome",message=f"Welcome to {group.name}",entity_type="group",entity_id=group.id)
    log_activity(db,user.id,"groups","group_member_added",f"Added {target.name} to {group.name}",entity_type="group",entity_id=group.id,target_user_id=target.id)
    db.commit()
    await notification_ws.send(member_id,{"type":"notification_refresh","reason":"group_joined","group_id":group.id})
    return {"message":"Member added","member":user_payload(target)}


@router.delete("/{group_id}/members/{member_id}")
def remove_member(group_id: int, member_id: int, ban: bool = False, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    actor=membership(db,group_id,user.id);target=membership(db,group_id,member_id);group=db.get(Group,group_id)
    if not actor or actor.role!="admin": raise HTTPException(403,"Admin access required")
    if not target: raise HTTPException(404,"Member not found")
    if member_id==group.owner_id or member_id==user.id: raise HTTPException(400,"You cannot remove this member")
    if ban and not db.query(GroupBan).filter(GroupBan.group_id==group_id,GroupBan.user_id==member_id).first(): db.add(GroupBan(group_id=group_id,user_id=member_id,banned_by_id=user.id))
    db.delete(target);db.commit();return {"message":"Member banned" if ban else "Member removed"}


@router.post("/{group_id}/members/{member_id}/mute")
def mute_member(group_id: int, member_id: int, hours: int = 24, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    actor=membership(db,group_id,user.id);target=membership(db,group_id,member_id)
    if not actor or actor.role!="admin": raise HTTPException(403,"Admin access required")
    if not target or target.role=="admin": raise HTTPException(400,"This member cannot be muted")
    target.posting_muted_until=None if hours==0 else datetime.utcnow()+timedelta(hours=max(1,min(hours,8760)))
    db.commit();return {"posting_muted_until":target.posting_muted_until}


@router.put("/{group_id}")
def update_group(group_id: int, data: GroupUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    actor=membership(db,group_id,user.id);group=db.get(Group,group_id)
    if not group: raise HTTPException(404,"Group not found")
    if not actor or actor.role!="admin": raise HTTPException(403,"Admin access required")
    if data.privacy not in PRIVACY or data.visibility not in VISIBILITY: raise HTTPException(400,"Invalid group settings")
    group.name=data.name.strip();group.description=(data.description or "").strip() or None;group.rules=(data.rules or "").strip() or None
    group.privacy=data.privacy;group.visibility=data.visibility;group.cover_url=data.cover_url
    group.approval_questions=json.dumps([x.strip() for x in data.approval_questions if x.strip()][:3],ensure_ascii=False)
    group.allow_anonymous_posts=data.allow_anonymous_posts;group.require_post_approval=data.require_post_approval
    db.commit();return group_payload(db,group,user,True)


@router.put("/{group_id}/cover")
def update_group_cover(group_id: int, data: GroupCoverUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    actor=membership(db,group_id,user.id);group=db.get(Group,group_id)
    if not group: raise HTTPException(404,"Group not found")
    if not actor or actor.role!="admin": raise HTTPException(403,"Admin access required")
    if not data.cover_url.startswith("/uploads/"): raise HTTPException(400,"Invalid uploaded cover URL")
    group.cover_url=data.cover_url;db.commit();db.refresh(group)
    log_activity(db,user.id,"groups","group_cover_updated",f"Updated the cover photo for {group.name}",entity_type="group",entity_id=group.id)
    db.commit()
    return {"cover_url":group.cover_url}


@router.get("/{group_id}/posts")
def list_posts(group_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    group = db.get(Group, group_id); member = membership(db, group_id, user.id) if group else None
    if not group or not can_view_content(group, member): raise HTTPException(403, "Join this group to view posts")
    hidden_ids={row.post_id for row in db.query(GroupPostHidden).filter(GroupPostHidden.user_id==user.id).all()}
    rows = db.query(GroupPost).filter(GroupPost.group_id == group_id, GroupPost.status == "published").order_by(GroupPost.created_at.desc()).limit(100).all()
    rows=[row for row in rows if row.id not in hidden_ids]
    result=[]
    for row in rows:
        author=db.get(User,row.author_id)
        reactions=db.query(GroupPostReaction).filter(GroupPostReaction.post_id==row.id).all();counts={};mine=None
        for reaction in reactions:
            counts[reaction.reaction]=counts.get(reaction.reaction,0)+1
            if reaction.user_id==user.id: mine=reaction.reaction
        comments=db.query(GroupPostComment).filter(GroupPostComment.post_id==row.id).order_by(GroupPostComment.created_at.asc()).all()
        result.append({"id":row.id,"content":row.content,"media_url":row.media_url,"media_type":row.media_type,"is_anonymous":row.is_anonymous,"is_pinned":row.is_pinned,"created_at":row.created_at,"author":None if row.is_anonymous else user_payload(author),"can_delete":row.author_id==user.id or (member and member.role in {"admin","moderator"}),"can_moderate":bool(member and member.role in {"admin","moderator"}),"my_reaction":mine,"reaction_counts":counts,"reactions_count":len(reactions),"comments":[{"id":comment.id,"content":comment.content,"created_at":comment.created_at,"author":user_payload(db.get(User,comment.author_id))} for comment in comments],"can_share":group.privacy=="public"})
    return result


@router.post("/{group_id}/posts")
def create_post(group_id: int, data: GroupPostCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    member = membership(db, group_id, user.id)
    if not member: raise HTTPException(403, "Join this group before posting")
    group=db.get(Group,group_id)
    if member.posting_muted_until and member.posting_muted_until>datetime.utcnow(): raise HTTPException(403,"Your posting permission is temporarily suspended")
    if data.is_anonymous and not group.allow_anonymous_posts: raise HTTPException(400,"Anonymous posting is disabled")
    if not data.content.strip() and not data.media_url: raise HTTPException(400, "Post cannot be empty")
    if data.media_type not in {"image", "video", "file", "gif"}: raise HTTPException(400, "Invalid media type")
    status="published" if member.role in {"admin","moderator"} or not group.require_post_approval else "pending"
    row=GroupPost(group_id=group_id,author_id=user.id,content=data.content.strip(),media_url=data.media_url,media_type=data.media_type,is_anonymous=data.is_anonymous,status=status)
    db.add(row);db.commit();db.refresh(row)
    return {"id":row.id,"status":status}


@router.delete("/{group_id}/posts/{post_id}")
def delete_post(group_id: int, post_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    member=membership(db,group_id,user.id);row=db.get(GroupPost,post_id)
    if not row or row.group_id!=group_id: raise HTTPException(404,"Post not found")
    if row.author_id!=user.id and (not member or member.role not in {"admin","moderator"}): raise HTTPException(403,"Not allowed")
    db.delete(row);db.commit();return {"message":"Post deleted"}


@router.post("/{group_id}/posts/{post_id}/pin")
def pin_post(group_id: int, post_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    member=membership(db,group_id,user.id);row=db.get(GroupPost,post_id)
    if not member or member.role not in {"admin","moderator"}: raise HTTPException(403,"Admin or moderator access required")
    if not row or row.group_id!=group_id: raise HTTPException(404,"Post not found")
    row.is_pinned=not row.is_pinned;db.commit()
    return {"is_pinned":row.is_pinned}


@router.post("/{group_id}/posts/{post_id}/react")
def react_to_post(group_id: int, post_id: int, data: ReactionIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    group=db.get(Group,group_id);row=db.get(GroupPost,post_id);member=membership(db,group_id,user.id) if group else None
    if not group or not row or row.group_id!=group_id or not can_view_content(group,member): raise HTTPException(404,"Post not found")
    if data.reaction not in REACTIONS: raise HTTPException(400,"Invalid reaction")
    existing=db.query(GroupPostReaction).filter(GroupPostReaction.post_id==post_id,GroupPostReaction.user_id==user.id).first()
    if existing and existing.reaction==data.reaction: db.delete(existing)
    elif existing: existing.reaction=data.reaction
    else: db.add(GroupPostReaction(post_id=post_id,user_id=user.id,reaction=data.reaction))
    db.commit();return {"message":"Reaction updated"}


@router.post("/{group_id}/posts/{post_id}/comments")
def comment_on_post(group_id: int, post_id: int, data: GroupCommentCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    group=db.get(Group,group_id);row=db.get(GroupPost,post_id);member=membership(db,group_id,user.id) if group else None
    if not group or not row or row.group_id!=group_id or not can_view_content(group,member): raise HTTPException(404,"Post not found")
    comment=GroupPostComment(post_id=post_id,author_id=user.id,content=data.content.strip());db.add(comment);db.commit();db.refresh(comment)
    return {"id":comment.id,"content":comment.content,"created_at":comment.created_at,"author":user_payload(user)}


@router.post("/{group_id}/posts/{post_id}/share")
def share_group_post(group_id: int, post_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    group=db.get(Group,group_id);row=db.get(GroupPost,post_id)
    if not group or not row or row.group_id!=group_id: raise HTTPException(404,"Post not found")
    if group.privacy!="public": raise HTTPException(403,"Private group posts cannot be shared")
    source=db.get(User,row.author_id);prefix=f"Shared from the public group {group.name}"
    content=f"{prefix}\n\n{row.content}".strip()
    post=Post(author_id=user.id,content=content,image_url=row.media_url if row.media_type in {"image","video","gif"} else None,media_type=row.media_type if row.media_type in {"image","video","gif"} else "image",privacy=Privacy.public)
    db.add(post);db.commit();return {"message":"Post shared to your timeline","post_id":post.id}


@router.post("/{group_id}/posts/{post_id}/moderate/{action}")
def moderate_post(group_id: int, post_id: int, action: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    actor=membership(db,group_id,user.id);row=db.get(GroupPost,post_id)
    if not actor or actor.role not in {"admin","moderator"}: raise HTTPException(403,"Admin or moderator access required")
    if not row or row.group_id!=group_id or row.status!="pending" or action not in {"approve","decline"}: raise HTTPException(404,"Pending post not found")
    if action=="approve": row.status="published"
    else: db.delete(row)
    db.commit();return {"status":"published" if action=="approve" else "declined"}


@router.post("/{group_id}/posts/{post_id}/hide")
def hide_post(group_id: int, post_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row=db.get(GroupPost,post_id)
    if not row or row.group_id!=group_id: raise HTTPException(404,"Post not found")
    if not db.query(GroupPostHidden).filter(GroupPostHidden.post_id==post_id,GroupPostHidden.user_id==user.id).first(): db.add(GroupPostHidden(post_id=post_id,user_id=user.id))
    db.commit();return {"message":"Post hidden"}


@router.post("/{group_id}/posts/{post_id}/report")
def report_post(group_id: int, post_id: int, data: GroupReportCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row=db.get(GroupPost,post_id)
    if not row or row.group_id!=group_id: raise HTTPException(404,"Post not found")
    db.add(GroupReport(group_id=group_id,reporter_id=user.id,post_id=post_id,reason=data.reason.strip()));db.commit()
    return {"message":"Report sent to group administrators"}


@router.post("/{group_id}/reports/{report_id}/resolve")
def resolve_report(group_id: int, report_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    actor=membership(db,group_id,user.id);report=db.get(GroupReport,report_id)
    if not actor or actor.role not in {"admin","moderator"}: raise HTTPException(403,"Admin or moderator access required")
    if not report or report.group_id!=group_id: raise HTTPException(404,"Report not found")
    report.status="resolved";db.commit();return {"message":"Report resolved"}


@router.post("/{group_id}/notifications")
def toggle_group_notifications(group_id: int, enabled: bool, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    member=membership(db,group_id,user.id)
    if not member: raise HTTPException(403,"Group membership required")
    member.notifications_enabled=enabled;db.commit();return {"notifications_enabled":enabled}
