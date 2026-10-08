"""Sandbox-only V1.1 transactional API. Do NOT expose directly on the internet."""
import os
import secrets
from datetime import datetime, timezone
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, Header
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, ForeignKey, String, Integer, DateTime, UniqueConstraint, select, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker, Session
from sqlalchemy.exc import IntegrityError

DB_URL = os.getenv('DATABASE_URL','sqlite:///./dev.db')
DEMO_KEY = os.getenv('DEMO_API_KEY','local-dev-only')
engine = create_engine(DB_URL, connect_args={'check_same_thread': False} if DB_URL.startswith('sqlite') else {},pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

class Base(DeclarativeBase): pass
class Customer(Base):
    __tablename__='customers'
    id:Mapped[int]=mapped_column(primary_key=True)
    tenant_id:Mapped[int]=mapped_column(Integer,index=True,default=1)
    name:Mapped[str]=mapped_column(String(120))
    industry:Mapped[str]=mapped_column(String(30),default='BEAUTY')
    referrer_id:Mapped[Optional[int]]=mapped_column(ForeignKey('customers.id'),nullable=True)
    wallet:Mapped['Wallet']=relationship(back_populates='customer',uselist=False)
class Wallet(Base):
    __tablename__='wallets'
    customer_id:Mapped[int]=mapped_column(ForeignKey('customers.id'),primary_key=True)
    prepaid_cents:Mapped[int]=mapped_column(Integer,default=0)
    points:Mapped[int]=mapped_column(Integer,default=0)
    customer:Mapped[Customer]=relationship(back_populates='wallet')
class Rule(Base):
    __tablename__='rules'
    id:Mapped[int]=mapped_column(primary_key=True)
    tenant_id:Mapped[int]=mapped_column(Integer,index=True,default=1)
    version:Mapped[int]=mapped_column(Integer)
    direct_reward_bps:Mapped[int]=mapped_column(Integer,default=500)
    max_point_discount_bps:Mapped[int]=mapped_column(Integer,default=5000)
    active:Mapped[int]=mapped_column(Integer,default=1)
    __table_args__=(UniqueConstraint('tenant_id','version'),)
class Purchase(Base):
    __tablename__='purchases'
    id:Mapped[int]=mapped_column(primary_key=True)
    tenant_id:Mapped[int]=mapped_column(Integer,default=1)
    customer_id:Mapped[int]=mapped_column(ForeignKey('customers.id'))
    amount_cents:Mapped[int]=mapped_column(Integer)
    points_used:Mapped[int]=mapped_column(Integer)
    prepaid_used_cents:Mapped[int]=mapped_column(Integer)
    external_paid_cents:Mapped[int]=mapped_column(Integer)
    reward_basis_cents:Mapped[int]=mapped_column(Integer)
    reward_points:Mapped[int]=mapped_column(Integer,default=0)
    referrer_id:Mapped[Optional[int]]=mapped_column(Integer,nullable=True)
    rule_version:Mapped[int]=mapped_column(Integer)
    status:Mapped[str]=mapped_column(String(30),default='PAID')
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
class Ledger(Base):
    __tablename__='wallet_ledger'
    id:Mapped[int]=mapped_column(primary_key=True)
    customer_id:Mapped[int]=mapped_column(ForeignKey('customers.id'),index=True)
    purchase_id:Mapped[Optional[int]]=mapped_column(Integer,nullable=True)
    kind:Mapped[str]=mapped_column(String(40))
    prepaid_delta_cents:Mapped[int]=mapped_column(Integer,default=0)
    points_delta:Mapped[int]=mapped_column(Integer,default=0)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
class RequestKey(Base):
    __tablename__='idempotency_keys'
    key:Mapped[str]=mapped_column(String(128),primary_key=True)
    operation:Mapped[str]=mapped_column(String(40))
    resource_id:Mapped[int]=mapped_column(Integer)

app=FastAPI(title='美容医美 AI 销售副驾 V1.1 / Sandbox',version='0.1.0')

def check_key(x_demo_key:Optional[str]=Header(default=None)):
    if not DEMO_KEY or not secrets.compare_digest(x_demo_key or '', DEMO_KEY):
        raise HTTPException(401,'开发环境 API 密钥无效')

def db():
    with SessionLocal() as s: yield s

def customer_or_404(s,cid):
    c=s.get(Customer,cid)
    if not c: raise HTTPException(404,'客户不存在')
    return c

def wallet_json(w):return {'customer_id':w.customer_id,'prepaid_cents':w.prepaid_cents,'points':w.points,'point_value_cents':100}

class CustomerIn(BaseModel):
    name:str=Field(min_length=1,max_length=120)
    industry:str='BEAUTY'
    referrer_id:Optional[int]=None
class TopupIn(BaseModel):
    customer_id:int
    amount_cents:int=Field(gt=0,le=100000000)
class PurchaseIn(BaseModel):
    customer_id:int
    amount_cents:int=Field(gt=0,le=100000000)
    desired_points:int=Field(default=0,ge=0)
    desired_prepaid_cents:int=Field(default=0,ge=0)
class RuleIn(BaseModel):
    direct_reward_bps:int=Field(ge=0,le=1500)
    max_point_discount_bps:int=Field(ge=0,le=5000)

@app.get('/health')
def health():return {'ok':True,'mode':'sandbox'}
@app.post('/api/v1/customers',dependencies=[Depends(check_key)])
def add_customer(payload:CustomerIn,s:Session=Depends(db)):
    if payload.industry not in ('BEAUTY','MEDICAL_BEAUTY'):raise HTTPException(422,'不支持的行业')
    if payload.referrer_id is not None:
        p=customer_or_404(s,payload.referrer_id)
        if p.industry!=payload.industry:raise HTTPException(422,'跨行业归因需单独审核')
    c=Customer(name=payload.name,industry=payload.industry,referrer_id=payload.referrer_id)
    s.add(c);s.flush();s.add(Wallet(customer_id=c.id));s.commit()
    return {'id':c.id,'name':c.name,'industry':c.industry,'direct_referrer_id':c.referrer_id}
@app.get('/api/v1/customers/{customer_id}',dependencies=[Depends(check_key)])
def get_customer(customer_id:int,s:Session=Depends(db)):
    c=customer_or_404(s,customer_id)
    return {'id':c.id,'name':c.name,'industry':c.industry,'direct_referrer_id':c.referrer_id,'wallet':wallet_json(c.wallet)}
@app.get('/api/v1/wallets/{customer_id}',dependencies=[Depends(check_key)])
def get_wallet(customer_id:int,s:Session=Depends(db)):
    return wallet_json(customer_or_404(s,customer_id).wallet)
@app.get('/api/v1/rules',dependencies=[Depends(check_key)])
def current_rule(s:Session=Depends(db)):
    rule=s.scalar(select(Rule).where(Rule.active==1).order_by(Rule.version.desc()))
    return {'version':rule.version,'direct_reward_bps':rule.direct_reward_bps,'max_point_discount_bps':rule.max_point_discount_bps}
@app.post('/api/v1/rules',dependencies=[Depends(check_key)])
def update_rule(inp:RuleIn,s:Session=Depends(db)):
    prior=s.scalar(select(Rule).order_by(Rule.version.desc()))
    if prior:prior.active=0
    n=Rule(version=(prior.version+1 if prior else 1),direct_reward_bps=inp.direct_reward_bps,max_point_discount_bps=inp.max_point_discount_bps)
    s.add(n);s.commit();return {'version':n.version,'status':'sandbox_rule_published'}

def existing(s,key,op):
    x=s.get(RequestKey,key)
    if x and x.operation!=op:raise HTTPException(409,'幂等键已用于其他操作')
    return x

@app.post('/api/v1/wallets/topup-demo',dependencies=[Depends(check_key)])
def topup_demo(inp:TopupIn,idempotency_key:str=Header(alias='Idempotency-Key'),s:Session=Depends(db)):
    # No payment provider integrated. Never call this "real recharge".
    if existing(s,idempotency_key,'topup'):return {'status':'duplicate_ignored'}
    c=customer_or_404(s,inp.customer_id)
    c.wallet.prepaid_cents+=inp.amount_cents
    s.add(Ledger(customer_id=c.id,kind='DEMO_TOPUP',prepaid_delta_cents=inp.amount_cents))
    s.add(RequestKey(key=idempotency_key,operation='topup',resource_id=c.id))
    try:s.commit()
    except IntegrityError:s.rollback();return {'status':'duplicate_ignored'}
    return wallet_json(c.wallet)

@app.post('/api/v1/orders/checkout-demo',dependencies=[Depends(check_key)])
def checkout(inp:PurchaseIn,idempotency_key:str=Header(alias='Idempotency-Key'),s:Session=Depends(db)):
    if existing(s,idempotency_key,'checkout'):
        record=s.get(RequestKey,idempotency_key)
        return order_json(s.get(Purchase,record.resource_id))
    c=customer_or_404(s,inp.customer_id)
    if c.industry!='BEAUTY':raise HTTPException(403,'医美奖励及抵扣默认关闭')
    rule=s.scalar(select(Rule).where(Rule.active==1).order_by(Rule.version.desc()))
    maxpoints=(inp.amount_cents*rule.max_point_discount_bps)//(10000*100)
    pts=min(inp.desired_points,c.wallet.points,maxpoints)
    prepaid=min(inp.desired_prepaid_cents,c.wallet.prepaid_cents,inp.amount_cents-pts*100)
    external=inp.amount_cents-pts*100-prepaid
    # external is a simulated payment; real checkout must verify PSP callback.
    c.wallet.points-=pts;c.wallet.prepaid_cents-=prepaid
    row=Purchase(customer_id=c.id,amount_cents=inp.amount_cents,points_used=pts,prepaid_used_cents=prepaid,external_paid_cents=external,reward_basis_cents=inp.amount_cents-pts*100,rule_version=rule.version)
    s.add(row);s.flush()
    if pts or prepaid:s.add(Ledger(customer_id=c.id,purchase_id=row.id,kind='ORDER_PAYMENT',prepaid_delta_cents=-prepaid,points_delta=-pts))
    s.add(RequestKey(key=idempotency_key,operation='checkout',resource_id=row.id))
    try:s.commit()
    except IntegrityError:s.rollback();raise HTTPException(409,'并发冲突；请查询原订单再重试')
    return order_json(row)

def order_json(o):
    return {'id':o.id,'status':o.status,'amount_cents':o.amount_cents,'points_used':o.points_used,'prepaid_used_cents':o.prepaid_used_cents,'external_paid_cents':o.external_paid_cents,'reward_basis_cents':o.reward_basis_cents,'reward_points':o.reward_points,'rule_version':o.rule_version}

@app.get('/api/v1/orders/{order_id}',dependencies=[Depends(check_key)])
def get_order(order_id:int,s:Session=Depends(db)):
    o=s.get(Purchase,order_id)
    if not o:raise HTTPException(404,'订单不存在')
    return order_json(o)

@app.post('/api/v1/orders/{order_id}/fulfill-demo',dependencies=[Depends(check_key)])
def fulfill(order_id:int,s:Session=Depends(db)):
    o=s.get(Purchase,order_id)
    if not o:raise HTTPException(404,'订单不存在')
    if o.status=='FULFILLED':return order_json(o)
    if o.status!='PAID':raise HTTPException(409,'订单当前不可履约')
    rule=s.scalar(select(Rule).where(Rule.version==o.rule_version))
    buyer=customer_or_404(s,o.customer_id)
    o.status='FULFILLED'
    if buyer.referrer_id:
        ref=customer_or_404(s,buyer.referrer_id)
        # 1 point = ¥1; no reward for credits and no indirect multi-level payout
        pts=(o.reward_basis_cents*rule.direct_reward_bps)//1000000
        if pts:
            ref.wallet.points+=pts
            o.reward_points=pts;o.referrer_id=ref.id
            s.add(Ledger(customer_id=ref.id,purchase_id=o.id,kind='DIRECT_REFERRAL_REWARD',points_delta=pts))
    s.commit();return order_json(o)

@app.post('/api/v1/orders/{order_id}/refund-demo',dependencies=[Depends(check_key)])
def refund(order_id:int,s:Session=Depends(db)):
    o=s.get(Purchase,order_id)
    if not o:raise HTTPException(404,'订单不存在')
    if o.status=='REFUNDED':return order_json(o)
    if o.status not in ('PAID','FULFILLED'):raise HTTPException(409,'不可退款')
    buyer=customer_or_404(s,o.customer_id)
    if o.referrer_id and o.reward_points:
        ref=customer_or_404(s,o.referrer_id)
        if ref.wallet.points<o.reward_points:raise HTTPException(409,'推荐积分已使用，转人工冲正处理，禁止扣充值本金')
        ref.wallet.points-=o.reward_points
        s.add(Ledger(customer_id=ref.id,purchase_id=o.id,kind='REWARD_REVERSAL',points_delta=-o.reward_points))
    buyer.wallet.points+=o.points_used
    buyer.wallet.prepaid_cents+=o.prepaid_used_cents
    s.add(Ledger(customer_id=buyer.id,purchase_id=o.id,kind='FULL_REFUND',points_delta=o.points_used,prepaid_delta_cents=o.prepaid_used_cents))
    o.status='REFUNDED';s.commit()
    return {**order_json(o),'external_refund_due_cents':o.external_paid_cents,'note':'外部支付仅为模拟，未发起真实退款'}

@app.get('/api/v1/wallets/{customer_id}/ledger',dependencies=[Depends(check_key)])
def wallet_ledger(customer_id:int,s:Session=Depends(db)):
    customer_or_404(s,customer_id)
    rows=s.scalars(select(Ledger).where(Ledger.customer_id==customer_id).order_by(Ledger.id)).all()
    return [{'id':x.id,'kind':x.kind,'purchase_id':x.purchase_id,'prepaid_delta_cents':x.prepaid_delta_cents,'points_delta':x.points_delta} for x in rows]

def init_db():
    Base.metadata.create_all(engine)
    with SessionLocal() as s:
        if not s.scalar(select(Rule.id).limit(1)):
            s.add(Rule(tenant_id=1,version=1,direct_reward_bps=500,max_point_discount_bps=5000));s.commit()

init_db()
