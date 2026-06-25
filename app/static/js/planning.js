let dragged=null;
document.addEventListener('dragstart',function(e){
  const item=e.target.closest('[data-event-id]');
  if(!item)return;
  dragged={event_type:item.dataset.eventType,event_id:item.dataset.eventId};
  item.classList.add('dragging');
});
document.addEventListener('dragend',function(e){
  const item=e.target.closest('[data-event-id]');
  if(item)item.classList.remove('dragging');
});
document.querySelectorAll('.drop-cell').forEach(function(cell){
  cell.addEventListener('dragover',function(e){e.preventDefault();cell.classList.add('drop-hover');});
  cell.addEventListener('dragleave',function(){cell.classList.remove('drop-hover');});
  cell.addEventListener('drop',function(e){
    e.preventDefault();cell.classList.remove('drop-hover');
    if(!dragged)return;
    const board=document.querySelector('.pro-scheduler');
    const payload={event_type:dragged.event_type,event_id:dragged.event_id,resource_type:cell.dataset.resourceType,resource_id:cell.dataset.resourceId,hour:cell.dataset.hour,date:board.dataset.date};
    fetch('/admin/planning/api/move',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)})
      .then(function(r){return r.json().then(function(j){return {ok:r.ok,body:j};});})
      .then(function(res){if(res.ok&&res.body.ok){window.location.reload();}else{alert(res.body.message||'Deplacement impossible');}})
      .catch(function(){alert('Erreur reseau');});
  });
});
