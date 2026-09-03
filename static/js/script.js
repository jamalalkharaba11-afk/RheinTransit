const form=document.getElementById("quoteForm");
if(form){
 const ids=["service","rooms","distance","floor","elevator"];
 const update=async()=>{const extras=[...document.querySelectorAll('input[name="extras"]:checked')].map(x=>x.value);
 const data={}; ids.forEach(id=>data[id]=document.getElementById(id).value); data.extras=extras;
 const r=await fetch("/api/calculate",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(data)});
 const d=await r.json(); document.getElementById("price").textContent=d.price.toFixed(2)+" €";};
 [...ids.map(x=>document.getElementById(x)),...document.querySelectorAll('input[name="extras"]')].forEach(x=>x.addEventListener("input",update));
 update();
}