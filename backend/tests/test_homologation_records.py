from sqlalchemy import select
from app.models.entities import Contract, Employee, Qualification, Skill, Unit
from app.services.seed import demo_id
from test_phase2 import context, headers, user_for


def record_inputs(ctx):
    with ctx['factory']() as session:
        person=session.get(Employee,demo_id('hh-0001'))
        pattern=session.scalar(select(Contract.work_pattern_id).where(Contract.employee_id==person.id))
        skill=session.scalar(select(Skill.id).order_by(Skill.id))
        qualification=session.scalar(select(Qualification.id).order_by(Qualification.id))
        return {'unit_id':person.unit_id,'department_id':person.department_id,'job_role_id':person.job_role_id}, pattern, skill, qualification


def test_specialized_records_round_trip_matches_forms(context):
    client=context['client']; auth=headers(context)
    fields,pattern,skill,qualification=record_inputs(context)
    created=client.post('/api/v1/employees',headers=auth,json=fields|{'name':'Pessoa fictícia homologação','registration':'HOM001'})
    assert created.status_code==201
    path='/api/v1/employees/'+created.json()['id']
    contract={'work_pattern_id':pattern,'weekly_minutes':2400,'base_salary_cents':150001,'employment_type':'teste','valid_from':'2026-11-01','valid_until':None,'assumption_source':'Hipótese sintética documentada'}
    key=auth|{'Idempotency-Key':'homologation-contract-1042'}
    first=client.post(path+'/contracts',headers=key,json=contract)
    assert first.status_code==201 and first.json()['validation_status']=='pending_review'
    assert client.post(path+'/contracts',headers=key,json=contract).json()['id']==first.json()['id']
    rows=client.get(path+'/contracts',headers=auth).json()['items']
    assert len(rows)==1 and rows[0]['base_salary_cents']==150001
    assert client.post(path+'/contracts',headers=auth,json=contract).status_code==409
    q={'qualification_id':qualification,'valid_from':'2026-11-01','valid_until':'2027-11-01','evidence':'Documento fictício de teste'}
    assert client.post(path+'/qualifications',headers=auth,json=q).status_code==201
    assert client.get(path+'/qualifications',headers=auth).json()['items'][0]['verification_status']=='pending_review'
    assert client.post(path+'/qualifications',headers=auth,json=q|{'verification_status':'validated'}).status_code==422
    assert client.post(path+'/skills',headers=auth,json={'skill_id':skill}).status_code==201
    assert client.get(path+'/skills',headers=auth).json()['items'][0]['skill_id']==skill


def test_specialized_records_enforce_role_and_unit_scope(context):
    fields,pattern,skill,qualification=record_inputs(context)
    user_for(context,'records-manager','manager',fields['unit_id'])
    path='/api/v1/employees/'+demo_id('hh-0001')
    limited=headers(context,'records-manager')
    assert context['client'].get(path+'/contracts',headers=limited).status_code==403
    for suffix,body in [('skills',{'skill_id':skill}),('qualifications',{'qualification_id':qualification,'valid_from':'2026-11-01','valid_until':'2027-11-01'})]:
        assert context['client'].post(path+'/'+suffix,headers=limited,json=body).status_code==403
    with context['factory'].begin() as session:
        unit=Unit(organization_id=context['org'],name='Unidade isolada homologação'); session.add(unit); session.flush(); unit_id=unit.id
    user_for(context,'records-other-unit','hr',unit_id)
    other=headers(context,'records-other-unit')
    assert context['client'].post(path+'/skills',headers=other,json={'skill_id':skill}).status_code==404
    assert context['client'].get(path+'/contracts',headers=other).status_code==404
