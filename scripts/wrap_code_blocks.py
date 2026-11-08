"""Set and verify native code-block wrapping without replacing text or blocks.

Run inside company_write.py's lock. The API and field mask are documented in
references/presentation.md. No retry is performed after an ambiguous write.
"""
import argparse
import json
import re
import subprocess
import sys


def cli(args):
    p=subprocess.run(['lark-cli',*args,'--as','user'],capture_output=True,text=True)
    if p.returncode:
        raise RuntimeError(p.stderr.strip() or p.stdout.strip())
    result=json.loads(p.stdout)
    if result.get('ok') is not True or result.get('identity')!='user':
        raise RuntimeError('Unexpected CLI status or identity')
    data=result['data']
    if isinstance(data,dict) and 'code' in data:
        if data['code']!=0:raise RuntimeError(str(data))
        data=data.get('data',{})
    return data


def snapshot(document):
    version=cli(['docs','+fetch','--doc',document,'--scope','outline'])['document']['revision_id']
    items=[];token=None;seen=set()
    while True:
        query={'document_revision_id':version,'page_size':500}
        if token:query['page_token']=token
        result=cli(['api','GET',f'/open-apis/docx/v1/documents/{document}/blocks','--params',json.dumps(query)])
        items.extend(result['items'])
        if not result.get('has_more'):break
        token=result.get('page_token')
        if not token or token in seen:raise RuntimeError('Incomplete or cyclic block pagination')
        seen.add(token)
    return version,{b['block_id']:b for b in items if b.get('block_type')==14 and 'code' in b}


def run(document,block_ids=None,inspect=False):
    if not re.fullmatch(r'[A-Za-z0-9_-]+',document):
        raise ValueError('Pass a docx document ID, not a URL')
    _,before=snapshot(document)
    targets=set(block_ids) if block_ids else set(before)
    if targets-set(before):raise ValueError('Requested IDs include missing or non-code blocks')
    pending=[bid for bid in sorted(targets) if before[bid]['code'].get('style',{}).get('wrap') is not True]
    if inspect:
        return {'document_id':document,'code_blocks':len(targets),'wrapped':len(targets)-len(pending),'pending':pending,'modified':False}
    for start in range(0,len(pending),50):
        batch=pending[start:start+50]
        revision,current=snapshot(document)
        if set(batch)-set(current):raise RuntimeError('Code block removed concurrently; stopped')
        for bid in batch:
            if current[bid]['code'].get('elements')!=before[bid]['code'].get('elements'):
                raise RuntimeError('Code text changed concurrently; stopped before write')
        body={'requests':[{'block_id':bid,'update_text_style':{'style':{'wrap':True},'fields':[5]}} for bid in batch]}
        args=['api','PATCH',f'/open-apis/docx/v1/documents/{document}/blocks/batch_update','--params',json.dumps({'document_revision_id':revision}),'--data',json.dumps(body)]
        cli(args+['--dry-run'])
        cli(args)
        _,check=snapshot(document)
        for bid in batch:
            if check.get(bid,{}).get('code',{}).get('style',{}).get('wrap') is not True:
                raise RuntimeError('Native wrap did not persist; do not replay blindly')
            if check[bid]['code'].get('elements')!=before[bid]['code'].get('elements'):
                raise RuntimeError('Code text differs after style update')
    revision,after=snapshot(document)
    for bid in targets:
        assert after[bid]['code'].get('style',{}).get('wrap') is True
        assert after[bid]['code'].get('elements')==before[bid]['code'].get('elements')
    return {'document_id':document,'revision':revision,'code_blocks':len(targets),'wrapped':len(targets),'updated':len(pending),'text_unchanged':True,'native_wrap_verified':True}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('document')
    parser.add_argument('--block-id',action='append',help='Target code block; repeat to restrict scope')
    parser.add_argument('--inspect',action='store_true',help='Read only; report current native wrap state')
    args=parser.parse_args()
    try:
        print(json.dumps(run(args.document,args.block_id,args.inspect),ensure_ascii=False))
    except (RuntimeError,ValueError,KeyError,AssertionError) as exc:
        sys.exit(f'代码块自动换行尚未核验完成：{exc}')
