const __vite__mapDeps=(i,m=__vite__mapDeps,d=(m.f||(m.f=["./designer-Bi7mkVZu.js","./index-DWowhpB8.js","./vue-BMGjCUij.js","./element-plus-BT5IgX0A.js","./element-plus-y9438Lsb.css","./axios-DhXgJQ-f.js","./index-DB2ysCNr.css"])))=>i.map(i=>d[i]);
import{b as z,p as y,_ as V}from"./index-DWowhpB8.js";import{r as u,c as A}from"./vue-BMGjCUij.js";function v(n){if(!n||typeof n!="object")return n;if(Array.isArray(n))return n.map(v);const i={};for(const r in n){const o=r.replace(/_([a-z])/g,(l,d)=>d.toUpperCase());i[o]=v(n[r])}return i}function P(n){if(!n||typeof n!="object")return n;if(Array.isArray(n))return n.map(P);const i={};for(const r in n){const o=r.replace(/[A-Z]/g,l=>"_"+l.toLowerCase());i[o]=P(n[r])}return i}const H=z("project",()=>{const n=u([]),i=u(null),r=u(!1),o=u(null),l=u(""),d=u(""),m=u("createdAt"),f=u("desc"),g=u(1),p=u(9),O=A(()=>[...n.value].sort((e,t)=>new Date(t.updatedAt||t.createdAt)-new Date(e.updatedAt||e.createdAt)).slice(0,5)),w=A(()=>{let e=[...n.value];if(l.value&&(e=e.filter(t=>(t.status||"").toLowerCase()===l.value.toLowerCase())),d.value){const t=d.value.toLowerCase();e=e.filter(a=>(a.name||"").toLowerCase().includes(t)||(a.description||"").toLowerCase().includes(t))}return e.sort((t,a)=>{const c=t[m.value]||"",s=a[m.value]||"";return m.value==="createdAt"||m.value==="updatedAt"?f.value==="desc"?new Date(s)-new Date(c):new Date(c)-new Date(s):f.value==="desc"?s.localeCompare(c):c.localeCompare(s)}),e}),D=A(()=>{const e=(g.value-1)*p.value,t=e+p.value;return w.value.slice(e,t)}),C=A(()=>Math.ceil(w.value.length/p.value));async function L(e=null){r.value=!0,o.value=null;try{const t=await y.list(e);return n.value=v(t.data||[]),n.value}catch(t){throw o.value=t.message||"Failed to load projects",t}finally{r.value=!1}}async function S(e){r.value=!0,o.value=null;try{const t=await y.get(e),a=v(t.data);i.value=a;const c=n.value.findIndex(s=>String(s.id)===String(e));return c!==-1&&(n.value[c]=a),a}catch(t){throw o.value=t.message||"Failed to load project",t}finally{r.value=!1}}async function I(e){r.value=!0,o.value=null;try{const t=await y.create(P(e)),a=v(t.data);return n.value.unshift(a),i.value=a,a}catch(t){throw o.value=t.message||"Failed to create project",t}finally{r.value=!1}}async function T(e,t){r.value=!0,o.value=null;try{const a=await y.update(e,P(t)),c=v(a.data),s=n.value.findIndex(h=>String(h.id)===String(e));return s!==-1&&(n.value[s]=c),i.value&&String(i.value.id)===String(e)&&(i.value=c),c}catch(a){throw o.value=a.message||"Failed to update project",a}finally{r.value=!1}}async function E(e){r.value=!0,o.value=null;try{await y.delete(e),n.value=n.value.filter(t=>String(t.id)!==String(e)),i.value&&String(i.value.id)===String(e)&&(i.value=null)}catch(t){throw o.value=t.message||"Failed to delete project",t}finally{r.value=!1}}function b(e){i.value=e}function x(){o.value=null}function j(e){e.status!==void 0&&(l.value=e.status),e.search!==void 0&&(d.value=e.search),e.sortBy!==void 0&&(m.value=e.sortBy),e.sortOrder!==void 0&&(f.value=e.sortOrder),e.currentPage!==void 0&&(g.value=e.currentPage),e.pageSize!==void 0&&(p.value=e.pageSize)}function k(){l.value="",d.value="",m.value="createdAt",f.value="desc",g.value=1,p.value=9}function U(e){g.value=Math.max(1,Math.min(e,C.value||1))}function F(e){p.value=e,g.value=1}async function M(e){try{const t=await S(e),{useDesignerStore:a}=await V(async()=>{const{useDesignerStore:s}=await import("./designer-Bi7mkVZu.js").then(h=>h.d);return{useDesignerStore:s}},__vite__mapDeps([0,1,2,3,4,5,6]),import.meta.url),c=a();return c.importFromProject(t),c}catch(t){throw o.value=t.message||"Failed to load design into designer",t}}async function _(e){const{useDesignerStore:t}=await V(async()=>{const{useDesignerStore:s}=await import("./designer-Bi7mkVZu.js").then(h=>h.d);return{useDesignerStore:s}},__vite__mapDeps([0,1,2,3,4,5,6]),import.meta.url),c=t().exportToProject();try{return await T(e,{design_data:c,updated_at:new Date().toISOString()})}catch(s){throw o.value=s.message||"Failed to save design",s}}return{projects:n,currentProject:i,isLoading:r,error:o,statusFilter:l,searchQuery:d,sortBy:m,sortOrder:f,currentPage:g,pageSize:p,recentProjects:O,filteredProjects:w,paginatedProjects:D,totalPages:C,loadProjects:L,loadProject:S,createProject:I,updateProject:T,deleteProject:E,setCurrentProject:b,clearError:x,setFilter:j,resetFilters:k,setPage:U,setPageSize:F,loadDesignIntoDesigner:M,saveDesignFromDesigner:_}}),N=[{id:1,name:"EV-Sedan Concept",description:"Electric sedan concept design with aerodynamic optimization and AI-driven styling exploration. This project focuses on creating a premium electric vehicle with exceptional efficiency and emotional design language.",status:"Active",createdAt:"2026-07-10",updatedAt:"2026-07-26",modelCount:12,carType:"Sedan",brand:"EVOLUTION",platform:"EV-Architecture V2",document:`# EV-Sedan Concept Project Brief

## Project Overview

This is a comprehensive design study for a premium electric sedan, leveraging AI-driven parametric modeling and real-time optimization.

### Key Objectives

- Achieve **Cd 0.18** aerodynamic efficiency
- Create emotional design language with sculptural surfaces
- Implement sustainable materials throughout

## Technical Specifications

| Parameter | Target Value |
|-----------|--------------|
| Overall Length | 4950mm |
| Wheelbase | 3000mm |
| Overall Width | 1900mm |
| Overall Height | 1450mm |
| Drag Coefficient | 0.18 |

## Design Philosophy

> "Less is more, but more is different."

The design philosophy emphasizes:
- **Pure Form**: Clean surfaces with minimal character lines
- **Lightness**: Visual weight reduction through clever surfacing
- **Advanced Technology**: Seamless integration of sensors and lighting

## Milestones

1. Phase 1: Hardpoint Definition (Complete)
2. Phase 2: Proportion Study (Complete)
3. Phase 3: Surface Development (In Progress)
4. Phase 4: Detail Design (Pending)
5. Phase 5: Validation & Release (Pending)

## Team

- **Lead Designer**: Alex Chen
- **Aerodynamics Engineer**: Sarah Wang
- **AI Engineer**: Michael Liu
- **Project Manager**: Emily Zhang`},{id:2,name:"SUV-A Platform",description:"Modular SUV platform design for mid-size family vehicle with hybrid powertrain options and advanced safety systems.",status:"Completed",createdAt:"2026-07-08",updatedAt:"2026-07-25",modelCount:24,carType:"SUV",brand:"EVOLUTION",platform:"SUV-Architecture",document:`# SUV-A Platform

## Overview

Multi-purpose SUV platform designed for family and adventure use with flexible seating configurations.

### Key Features

- **Modular Platform Architecture**
- **Hybrid Powertrain Options**
- **Advanced Safety Systems**
- **All-Wheel Drive Standard**

## Capabilities

- 5-7 seat configurations
- Up to 800km electric range
- 3,500kg towing capacity
- Level 2+ autonomous driving`},{id:3,name:"Sports Coupe V2",description:"Second generation sports coupe design study focusing on lightweight materials and extreme performance.",status:"Active",createdAt:"2026-07-05",updatedAt:"2026-07-24",modelCount:8,carType:"Coupe",brand:"EVOLUTION",platform:"Sport-Architecture",document:`# Sports Coupe V2

## Design Study

Aggressive proportions with low center of gravity and aerodynamic efficiency.

### Performance Targets

- 0-100 km/h: < 3.0s
- Top Speed: 320 km/h
- Power: 650 kW

### Materials

- Carbon fiber monocoque
- Aluminum subframes
- Active aerodynamics`},{id:4,name:"Hatchback Design",description:"Compact hatchback urban vehicle concept with focus on interior space optimization and city maneuverability.",status:"Draft",createdAt:"2026-07-02",updatedAt:"2026-07-23",modelCount:3,carType:"Hatchback",brand:"EVOLUTION",platform:"City-Platform",document:""},{id:5,name:"Crossover Study",description:"Crossover SUV coupe variant exploration combining SUV practicality with coupe styling.",status:"Completed",createdAt:"2026-06-28",updatedAt:"2026-07-22",modelCount:18,carType:"Crossover",brand:"EVOLUTION",platform:"Crossover-Architecture",document:""},{id:6,name:"Pickup Truck EV",description:"Electric pickup truck design program with innovative cargo solutions and off-road capability.",status:"Draft",createdAt:"2026-06-25",updatedAt:"2026-07-21",modelCount:1,carType:"Pickup",brand:"EVOLUTION",platform:"Truck-Architecture",document:""},{id:7,name:"Roadster Concept",description:"Two-seater roadster sports car design with classic proportions and modern electric powertrain.",status:"Active",createdAt:"2026-06-20",updatedAt:"2026-07-20",modelCount:15,carType:"Roadster",brand:"EVOLUTION",platform:"Roadster-Platform",document:`# Roadster Concept

## Vision

A modern interpretation of the classic roadster experience.

### Design Principles

- Long hood, short deck
- Perfect 50:50 weight distribution
- Minimalist interior
- Open-air driving experience`},{id:8,name:"Minivan Design",description:"Family-oriented minivan interior and exterior design focusing on comfort, safety, and versatility.",status:"Completed",createdAt:"2026-06-15",updatedAt:"2026-07-19",modelCount:20,carType:"MPV",brand:"EVOLUTION",platform:"MPV-Architecture",document:""},{id:9,name:"City Car EV",description:"Ultra-compact city electric vehicle designed for urban mobility with minimal environmental footprint.",status:"Draft",createdAt:"2026-06-10",updatedAt:"2026-07-18",modelCount:5,carType:"CityCar",brand:"EVOLUTION",platform:"Micro-Platform",document:""},{id:10,name:"Luxury Limousine",description:"Flagship luxury limousine with autonomous driving capabilities and premium interior experience.",status:"Active",createdAt:"2026-06-05",updatedAt:"2026-07-17",modelCount:10,carType:"Limousine",brand:"EVOLUTION",platform:"Luxury-Architecture",document:`# Luxury Limousine

## Flagship Model

The ultimate expression of luxury and technology.

### Interior Features

- Rear-seat entertainment system
- Premium leather upholstery
- Ambient lighting
- Air purification system
- Massage seats

### Technology

- Level 4 autonomous driving
- 5G connectivity
- AI assistant
- Biometric authentication`}],W=n=>{const i=parseInt(n);return N.find(r=>r.id===i)||null};export{W as g,N as m,H as u};
