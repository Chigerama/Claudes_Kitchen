// Run on https://www.woolworths.com.au/shop/myaccount/myorders/<id> after it loads (the order API only answers from that order's own page).
// Builds window.__W = JSON {id:{date,status,lines}}; read it in 900-char slices. Only grocery lines are kept (no address/payment/rewards data).
await new Promise(r=>setTimeout(r,2500));
{const id=location.pathname.match(/(\d+)$/)[1]; const j=await (await fetch('https://prod.mobile-api.woolworths.com.au/wow/v1/orders/api/orders/'+id,{credentials:'include'})).json();
const nm=o=>[o.Name,o.Size].filter(Boolean).join(' ').trim(); const r2=x=>Math.round(x*100)/100; const L=[];
for(const p of j.OrderProducts){const o=p.Ordered,s=p.Supplied||{};const kg=/KG/i.test(o.ListPrice?.Measure||'');const own=r2((s.Quantity||0)-(s.SubstitutedQuantity||0));
 const own$=r2((s.Total||0)-(s.Substitutions||[]).reduce((a,x)=>a+(x.Total||0),0));
 L.push({code:o.StockCode,name:nm(o),ordered:o.Quantity,supplied:own,price:r2(o.SalePrice?.Value||o.ListPrice?.Value||0),amount:own$,...(kg?{kg:1}:{})});
 for(const x of s.Substitutions||[]) L.push({code:x.StockCode,name:nm(x),ordered:x.Quantity,supplied:x.Quantity,price:r2(x.SalePrice?.Value||0),amount:r2(x.Total||0),sub:1});}
const d=(j.ProjectedDeliveryTime?.OriginalStartTime||j.CreatedDate).slice(0,10);
window.__W=JSON.stringify({[id]:{date:d,status:j.CurrentStatus,lines:L}}); __W.length+' '+d+' '+j.CurrentStatus+' $'+L.reduce((a,x)=>a+x.amount,0).toFixed(2)}
