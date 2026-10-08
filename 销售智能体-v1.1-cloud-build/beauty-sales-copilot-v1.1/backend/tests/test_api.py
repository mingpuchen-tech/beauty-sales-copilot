import os
os.environ['DATABASE_URL']='sqlite:///./test_v11.db'
os.environ['DEMO_API_KEY']='test-only'
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app, Base, engine, init_db
import pytest

@pytest.fixture(autouse=True)
def reset():
    Base.metadata.drop_all(engine);init_db();yield

@pytest.fixture
def api():
    c=TestClient(app);c.headers.update({'X-Demo-Key':'test-only'});return c

def make(c,name,ref=None,industry='BEAUTY'):
    r=c.post('/api/v1/customers',json={'name':name,'referrer_id':ref,'industry':industry});assert r.status_code==200,r.text;return r.json()['id']

def test_wallet_checkout_reward_and_idempotency(api):
    a=make(api,'A');b=make(api,'B',a);c=make(api,'C',b)
    r=api.post('/api/v1/wallets/topup-demo',headers={'Idempotency-Key':'fund-1'},json={'customer_id':c,'amount_cents':200000});assert r.status_code==200
    assert api.post('/api/v1/wallets/topup-demo',headers={'Idempotency-Key':'fund-1'},json={'customer_id':c,'amount_cents':200000}).json()['status']=='duplicate_ignored'
    order=api.post('/api/v1/orders/checkout-demo',headers={'Idempotency-Key':'sale-1'},json={'customer_id':c,'amount_cents':100000,'desired_points':10000,'desired_prepaid_cents':100000});assert order.status_code==200,order.text
    o=order.json();assert o['prepaid_used_cents']==100000 and o['points_used']==0
    assert api.post('/api/v1/orders/checkout-demo',headers={'Idempotency-Key':'sale-1'},json={'customer_id':c,'amount_cents':100000,'desired_points':10000,'desired_prepaid_cents':100000}).json()['id']==o['id']
    fulfilled=api.post(f"/api/v1/orders/{o['id']}/fulfill-demo").json()
    assert fulfilled['reward_points']==50  # ¥1000 * 5% = 50 points
    assert api.get(f'/api/v1/wallets/{b}').json()['points']==50
    assert api.get(f'/api/v1/wallets/{a}').json()['points']==0 # indirect no payout
    api.post(f"/api/v1/orders/{o['id']}/fulfill-demo")
    assert api.get(f'/api/v1/wallets/{b}').json()['points']==50
    refund=api.post(f"/api/v1/orders/{o['id']}/refund-demo")
    assert refund.status_code==200
    assert api.get(f'/api/v1/wallets/{b}').json()['points']==0
    assert api.get(f'/api/v1/wallets/{c}').json()['prepaid_cents']==200000

def test_points_cap_and_reward_excludes_points(api):
    a=make(api,'A');b=make(api,'B',a)
    from app.main import SessionLocal, Wallet
    with SessionLocal() as s:
        s.get(Wallet,b).points=3000;s.commit()
    r=api.post('/api/v1/orders/checkout-demo',headers={'Idempotency-Key':'cap-test'},json={'customer_id':b,'amount_cents':200000,'desired_points':3000,'desired_prepaid_cents':0})
    assert r.status_code==200,r.text
    o=r.json();assert o['points_used']==1000 # 50% max at 1 point=¥1
    assert o['external_paid_cents']==100000
    assert api.post(f"/api/v1/orders/{o['id']}/fulfill-demo").json()['reward_points']==50

def test_rule_version_lock_and_medical_disabled(api):
    a=make(api,'A');b=make(api,'B',a)
    o=api.post('/api/v1/orders/checkout-demo',headers={'Idempotency-Key':'order-v'},json={'customer_id':b,'amount_cents':100000}).json()
    x=api.post('/api/v1/rules',json={'direct_reward_bps':300,'max_point_discount_bps':3000});assert x.status_code==200
    assert api.post(f"/api/v1/orders/{o['id']}/fulfill-demo").json()['reward_points']==50
    m=make(api,'medical',industry='MEDICAL_BEAUTY')
    assert api.post('/api/v1/orders/checkout-demo',headers={'Idempotency-Key':'med-1'},json={'customer_id':m,'amount_cents':10000}).status_code==403

def test_refund_blocked_if_earned_points_spent(api):
    a=make(api,'A');b=make(api,'B',a)
    o=api.post('/api/v1/orders/checkout-demo',headers={'Idempotency-Key':'order-earn'},json={'customer_id':b,'amount_cents':200000}).json()
    api.post(f"/api/v1/orders/{o['id']}/fulfill-demo")
    spend=api.post('/api/v1/orders/checkout-demo',headers={'Idempotency-Key':'spend-earn'},json={'customer_id':a,'amount_cents':10000,'desired_points':100})
    assert spend.json()['points_used']==50
    assert api.post(f"/api/v1/orders/{o['id']}/refund-demo").status_code==409
    assert api.get(f'/api/v1/orders/{o["id"]}').json()['status']=='FULFILLED'
