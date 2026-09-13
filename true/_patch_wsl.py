p='/home/redou/QuantLive/app/api/admin_app.py'
s=open(p,encoding='utf-8').read()
old='''async function load(){
  const r=await fetch(qp("options"),{headers:hdr()});
  if(!r.ok){toast("403 accès refusé");return;}
  const d=await r.json();OPT=d.options||{};SCHEMA=d.schema||[];PWPROTECT=!!d.password_protected;
  if(PWPROTECT && !TOKEN){document.body.classList.add("locked");document.getElementById("lockbox").style.display="block";}
  else{document.body.classList.remove("locked");document.getElementById("lockbox").style.display=PWPROTECT?"block":"none";}
  if(!CAT || (!SCHEMA.some(s=>s.category===CAT) && CAT!=="Monitoring")){CAT=(SCHEMA[0]||{}).category||"Trading";}
  renderTabs();render();
}'''
new='''async function load(){
 try{
  const r=await fetch(qp("options"),{headers:hdr()});
  if(!r.ok){toast("403 accès refusé");return;}
  const d=await r.json();OPT=d.options||{};SCHEMA=d.schema||[];PWPROTECT=!!d.password_protected;
  if(PWPROTECT && !TOKEN){document.body.classList.add("locked");document.getElementById("lockbox").style.display="block";}
  else{document.body.classList.remove("locked");document.getElementById("lockbox").style.display=PWPROTECT?"block":"none";}
  if(!CAT || (!SCHEMA.some(s=>s.category===CAT) && CAT!=="Monitoring")){CAT=(SCHEMA[0]||{}).category||"Trading";}
  renderTabs();render();
 }catch(e){console.error("load() exception:",e);toast("erreur chargement: "+e.message);}
}'''
if old in s:
    s=s.replace(old,new)
    oldr='''function render(){
  const showMon = (CAT==="Monitoring");'''
    newr='''function render(){
 try{
  const showMon = (CAT==="Monitoring");'''
    s=s.replace(oldr,newr)
    oldend='''  document.getElementById("cancel").disabled=n===0;
}'''
    newend='''  document.getElementById("cancel").disabled=n===0;
 }catch(e){console.error("render() exception:",e);}
}'''
    s=s.replace(oldend,newend)
    open(p,'w',encoding='utf-8').write(s)
    print('WSL PATCH APPLIED')
else:
    print('WSL OLD NOT FOUND')
