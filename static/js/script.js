const menuToggle=document.querySelector('.menu-toggle');
const nav=document.getElementById('mainNav');
if(menuToggle && nav){
  const setMenu=(open)=>{
    menuToggle.setAttribute('aria-expanded',String(open));
    menuToggle.setAttribute('aria-label',open?'Menü schließen':'Menü öffnen');
    nav.classList.toggle('open',open);
    document.body.classList.toggle('menu-open',open);
  };
  menuToggle.addEventListener('click',()=>setMenu(menuToggle.getAttribute('aria-expanded')!=='true'));
  nav.querySelectorAll('a').forEach(a=>a.addEventListener('click',()=>setMenu(false)));
  document.addEventListener('keydown',e=>{if(e.key==='Escape') setMenu(false);});
  document.addEventListener('click',e=>{if(nav.classList.contains('open') && !nav.contains(e.target) && !menuToggle.contains(e.target)) setMenu(false);});
}

const form=document.getElementById("quoteForm");
if(form){
 const ids=["service","rooms","distance","floor","elevator"];
 const update=async()=>{const extras=[...document.querySelectorAll('input[name="extras"]:checked')].map(x=>x.value);
 const data={}; ids.forEach(id=>data[id]=document.getElementById(id).value); data.extras=extras;
 try{const r=await fetch("/api/calculate",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(data)}); const d=await r.json(); document.getElementById("price").textContent=d.price.toFixed(2)+" €";}catch(e){document.getElementById("price").textContent="— €";}};
 [...ids.map(x=>document.getElementById(x)),...document.querySelectorAll('input[name="extras"]')].forEach(x=>x.addEventListener("input",update));
 update();
}
