<template>
  <div ref="containerRef" class="car-3d-container">
    <div class="controls-overlay">
      <div class="control-btn" @click="resetView" title="重置视角">
        <el-icon><RefreshRight /></el-icon>
      </div>
      <div class="control-btn" @click="toggleAutoRotate" :class="{ active: autoRotate }" title="自动旋转">
        <el-icon><Refresh /></el-icon>
      </div>
      <div class="control-btn" @click="showWireframe = !showWireframe" :class="{ active: showWireframe }" title="显示网格">
        <el-icon><Grid /></el-icon>
      </div>
    </div>
    <div class="info-overlay">
      <span>拖拽旋转 | 滚轮缩放 | 右键平移</span>
    </div>
  </div>
</template>

<script setup>import { ref, onMounted, onUnmounted, watch } from 'vue';
import * as THREE from 'three';
import { RefreshRight, Refresh, Grid } from '@element-plus/icons-vue';
const props = defineProps({
 carParams: { type: Object, required: true },
 componentParams: { type: Object, required: true },
 angleParams: { type: Object, required: true },
 carType: { type: String, default: 'sedan' },
 carColor: { type: String, default: '#00d9ff' }
});
const containerRef = ref(null);
const showWireframe = ref(false);
const autoRotate = ref(true);
let scene, camera, renderer, carGroup;
let animationId = null;
let isDragging = false;
let previousMousePosition = { x: 0, y: 0 };
let targetRotation = { x: 0.5, y: 1.0 };
let currentRotation = { x: 0.5, y: 1.0 };
let targetDistance = 9;
let currentDistance = 9;
let targetPosition = { x: 0, y: 0 };
let currentPosition = { x: 0, y: 0 };
const colors = {
 sedan: '#00d9ff',
 suv: '#8b5cf6',
 coupe: '#ff6b6b',
 mpv: '#00ff88',
 sport: '#ffc107',
 pickup: '#e6a800'
};
const createCarGeometry = () => {
 const L = props.carParams.overall_length / 1000;
 const W = props.carParams.overall_width / 1000;
 const H = props.carParams.overall_height / 1000;
 const WB = props.carParams.wheel_base / 1000;
  const track = props.carParams.track_width / 1000;
  const FO = props.carParams.front_overhang / 1000;
  const RO = props.carParams.rear_overhang / 1000;
 const hoodLen = props.componentParams.hood_length / 1000;
 const roofH = props.componentParams.roof_height / 1000;
 const wheelD = props.componentParams.wheel_diameter / 1000;
 const gc = props.componentParams.ground_clearance / 1000;
 const wAngle = props.angleParams.windshield_angle;
 const rAngle = props.angleParams.rear_window_angle;
 const carGroup = new THREE.Group();
 const bodyColor = new THREE.Color(colors[props.carType] || props.carColor);
 const metallicMaterial = new THREE.MeshStandardMaterial({
 color: bodyColor,
 metalness: 0.3,
 roughness: 0.2,
 envMapIntensity: 1.0
 });
 const glassMaterial = new THREE.MeshStandardMaterial({
 color: 0x64c8ff,
 metalness: 0.1,
 roughness: 0.1,
 transparent: true,
 opacity: 0.3
 });
 const wheelMaterial = new THREE.MeshStandardMaterial({
 color: 0x1a1a2e,
 metalness: 0.8,
 roughness: 0.4
 });
 const rimMaterial = new THREE.MeshStandardMaterial({
 color: 0x888888,
 metalness: 0.9,
 roughness: 0.3
 });
 const lightMaterial = new THREE.MeshStandardMaterial({
 color: 0xffffff,
 emissive: 0xffff00,
 emissiveIntensity: 1.5,
 metalness: 0.1,
 roughness: 0.1
 });
 const redLightMaterial = new THREE.MeshStandardMaterial({
 color: 0xff0000,
 emissive: 0xff0000,
 emissiveIntensity: 1.0,
 metalness: 0.1,
 roughness: 0.1
 });
 const frontWheelX = -WB / 2;
  const rearWheelX = WB / 2;
  const halfTrack = track / 2;
  const frontX = frontWheelX - FO;
  const rearX = rearWheelX + RO;
  const bodyLength = rearX - frontX;
  const midX = (frontX + rearX) / 2;
 // 车身基础形状
 let bodyGeometry;
 if (props.carType === 'sedan') {
 bodyGeometry = new THREE.CapsuleGeometry(W / 2 - 0.05, bodyLength - 0.4, 4, 16);
 bodyGeometry.rotateZ(Math.PI / 2);
 }
 else if (props.carType === 'suv') {
 bodyGeometry = new THREE.CapsuleGeometry(W / 2 - 0.08, bodyLength - 0.5, 4, 16);
 bodyGeometry.rotateZ(Math.PI / 2);
 }
 else if (props.carType === 'coupe') {
 const shape = new THREE.Shape();
 const roofCurve = 0.3;
 shape.moveTo(frontX, -W / 2 + 0.1);
 shape.bezierCurveTo(frontX, -W / 2 + 0.1, midX - bodyLength / 4, -W / 2 + 0.1, midX, -W / 2 + roofCurve);
 shape.bezierCurveTo(midX + bodyLength / 4, -W / 2 + roofCurve, rearX, -W / 2 + 0.2, rearX, -W / 2 + 0.2);
 shape.lineTo(rearX, W / 2 - 0.1);
 shape.lineTo(frontX, W / 2 - 0.1);
 shape.closePath();
 const extrudeSettings = { depth: H * 0.6, bevelEnabled: true, bevelSegments: 3, steps: 2, bevelSize: 0.05, bevelThickness: 0.05 };
 bodyGeometry = new THREE.ExtrudeGeometry(shape, extrudeSettings);
 }
 else if (props.carType === 'mpv') {
 bodyGeometry = new THREE.BoxGeometry(bodyLength - 0.3, W - 0.15, H * 0.7);
 }
 else if (props.carType === 'sport') {
 const shape = new THREE.Shape();
 shape.moveTo(frontX, -W / 2 + 0.05);
 shape.bezierCurveTo(frontX + 0.2, -W / 2 + 0.05, midX - bodyLength / 4, -W / 2 + 0.4, midX, -W / 2 + 0.35);
 shape.bezierCurveTo(midX + bodyLength / 4, -W / 2 + 0.35, rearX - 0.2, -W / 2 + 0.1, rearX, -W / 2 + 0.1);
 shape.lineTo(rearX, W / 2 - 0.05);
 shape.lineTo(frontX, W / 2 - 0.05);
 shape.closePath();
 const extrudeSettings = { depth: H * 0.5, bevelEnabled: true, bevelSegments: 3, steps: 2, bevelSize: 0.05, bevelThickness: 0.05 };
 bodyGeometry = new THREE.ExtrudeGeometry(shape, extrudeSettings);
 }
 else {
 bodyGeometry = new THREE.BoxGeometry(bodyLength - 0.4, W - 0.15, H * 0.6);
 }
 const body = new THREE.Mesh(bodyGeometry, metallicMaterial);
 body.position.y = gc + H * 0.35;
 carGroup.add(body);
 // 车顶
 let roofHeight = props.carType === 'suv' ? H * 0.25 : props.carType === 'mpv' ? H * 0.3 : H * 0.18;
 let roofWidth = props.carType === 'mpv' ? W - 0.18 : W - 0.1;
 let roofLength = props.carType === 'pickup' ? WB / 2 - 0.3 : bodyLength * 0.45;
  const roofGeometry = new THREE.BoxGeometry(roofLength, roofWidth, roofHeight);
  const roof = new THREE.Mesh(roofGeometry, metallicMaterial);
  roof.position.set(midX, gc + H * 0.55, 0);
 carGroup.add(roof);
 // 发动机盖
 const hoodGeometry = new THREE.CapsuleGeometry(W / 2 - 0.15, hoodLen * 0.8, 2, 8);
 hoodGeometry.rotateZ(Math.PI / 2);
 const hood = new THREE.Mesh(hoodGeometry, metallicMaterial);
  hood.position.set(frontX + hoodLen * 0.45, gc + H * 0.4, 0);
 hood.rotation.x = -wAngle * Math.PI / 180 * 0.3;
 carGroup.add(hood);
 // 挡风玻璃
 const windShieldGeometry = new THREE.BoxGeometry(0.03, W - 0.12, H * 0.25);
 const windShield = new THREE.Mesh(windShieldGeometry, glassMaterial);
 const windAngleRad = wAngle * Math.PI / 180;
  windShield.position.set(frontX + hoodLen - 0.1, gc + H * 0.5, 0);
 windShield.rotation.x = -Math.PI / 2 + windAngleRad;
 carGroup.add(windShield);
 // 后窗
 const rearWindowGeometry = new THREE.BoxGeometry(0.03, W - 0.12, H * 0.2);
 const rearWindow = new THREE.Mesh(rearWindowGeometry, glassMaterial);
 const rearAngleRad = rAngle * Math.PI / 180;
  rearWindow.position.set(rearX - 0.6, gc + H * 0.5, 0);
 rearWindow.rotation.x = Math.PI / 2 - rearAngleRad;
 carGroup.add(rearWindow);
 // 车门
 const doorHeight = props.carType === 'suv' ? H * 0.45 : props.carType === 'mpv' ? H * 0.45 : H * 0.35;
 const doorWidth = W - 0.08;
 const doorFront = new THREE.Mesh(new THREE.BoxGeometry(hoodLen * 0.5, doorWidth, doorHeight), metallicMaterial);
 doorFront.position.set(-WB / 4, gc + H * 0.35, W / 2 - 0.04);
 carGroup.add(doorFront);
 const doorFrontInner = new THREE.Mesh(new THREE.BoxGeometry(hoodLen * 0.5, doorWidth, doorHeight), glassMaterial);
 doorFrontInner.position.set(-WB / 4, gc + H * 0.45, W / 2 - 0.035);
 carGroup.add(doorFrontInner);
 const doorRear = new THREE.Mesh(new THREE.BoxGeometry(hoodLen * 0.45, doorWidth, doorHeight), metallicMaterial);
 doorRear.position.set(WB / 4, gc + H * 0.35, W / 2 - 0.04);
 carGroup.add(doorRear);
 const doorRearInner = new THREE.Mesh(new THREE.BoxGeometry(hoodLen * 0.45, doorWidth, doorHeight), glassMaterial);
 doorRearInner.position.set(WB / 4, gc + H * 0.45, W / 2 - 0.035);
 carGroup.add(doorRearInner);
 // 左侧车门镜像
 const doorFrontL = doorFront.clone();
 doorFrontL.position.z = -W / 2 + 0.04;
 carGroup.add(doorFrontL);
 const doorFrontInnerL = doorFrontInner.clone();
 doorFrontInnerL.position.z = -W / 2 + 0.035;
 carGroup.add(doorFrontInnerL);
 const doorRearL = doorRear.clone();
 doorRearL.position.z = -W / 2 + 0.04;
 carGroup.add(doorRearL);
 const doorRearInnerL = doorRearInner.clone();
 doorRearInnerL.position.z = -W / 2 + 0.035;
 carGroup.add(doorRearInnerL);
 // 车轮
 const createWheel = (x, z) => {
 const wheelGroup = new THREE.Group();
 const tireGeometry = new THREE.CylinderGeometry(wheelD / 2 - 0.03, wheelD / 2 - 0.03, 0.35, 32);
 tireGeometry.rotateX(Math.PI / 2);
 const tire = new THREE.Mesh(tireGeometry, wheelMaterial);
 wheelGroup.add(tire);
 const rimGeometry = new THREE.CylinderGeometry(wheelD / 4, wheelD / 4, 0.3, 12);
 rimGeometry.rotateX(Math.PI / 2);
 const rim = new THREE.Mesh(rimGeometry, rimMaterial);
 wheelGroup.add(rim);
 const spokeGeometry = new THREE.BoxGeometry(wheelD / 2 - 0.05, 0.02, 0.32);
 for (let i = 0; i < 5; i++) {
 const spoke = new THREE.Mesh(spokeGeometry, rimMaterial);
 spoke.rotation.y = (i * Math.PI * 2) / 5;
 wheelGroup.add(spoke);
 }
 wheelGroup.position.set(x, gc + wheelD / 2 - 0.05, z);
 return wheelGroup;
 };
 carGroup.add(createWheel(frontWheelX, halfTrack));
 carGroup.add(createWheel(frontWheelX, -halfTrack));
 carGroup.add(createWheel(rearWheelX, halfTrack));
 carGroup.add(createWheel(rearWheelX, -halfTrack));
 // 前灯
 const headlightGeometry = new THREE.BoxGeometry(0.3, 0.1, 0.08);
 const headlightL = new THREE.Mesh(headlightGeometry, lightMaterial);
  headlightL.position.set(frontX + 0.15, gc + H * 0.55, W / 2 - 0.08);
 carGroup.add(headlightL);
 const headlightR = headlightL.clone();
 headlightR.position.z = -W / 2 + 0.08;
 carGroup.add(headlightR);
 // 尾灯
 const taillightGeometry = new THREE.BoxGeometry(0.25, 0.12, 0.06);
 const taillightL = new THREE.Mesh(taillightGeometry, redLightMaterial);
  taillightL.position.set(rearX - 0.15, gc + H * 0.5, W / 2 - 0.08);
 carGroup.add(taillightL);
 const taillightR = taillightL.clone();
 taillightR.position.z = -W / 2 + 0.08;
 carGroup.add(taillightR);
 // 保险杠
 const bumperGeometry = new THREE.BoxGeometry(bodyLength * 0.95, 0.15, 0.08);
  const frontBumper = new THREE.Mesh(bumperGeometry, metallicMaterial);
  frontBumper.position.set(frontX + 0.3, gc + H * 0.15, 0);
  carGroup.add(frontBumper);
  const rearBumper = new THREE.Mesh(bumperGeometry, metallicMaterial);
  rearBumper.position.set(rearX - 0.3, gc + H * 0.15, 0);
 carGroup.add(rearBumper);
 // 后视镜
 const mirrorGeometry = new THREE.SphereGeometry(0.08, 16, 16);
 const mirrorL = new THREE.Mesh(mirrorGeometry, metallicMaterial);
  mirrorL.position.set(frontWheelX + WB / 4, gc + H * 0.55, W / 2 + 0.08);
 carGroup.add(mirrorL);
 const mirrorR = mirrorL.clone();
 mirrorR.position.z = -W / 2 - 0.08;
 carGroup.add(mirrorR);
 // 皮卡货斗
 if (props.carType === 'pickup') {
    const bedGeometry = new THREE.BoxGeometry(bodyLength * 0.35, W - 0.2, H * 0.35);
    const bed = new THREE.Mesh(bedGeometry, metallicMaterial);
    bed.position.set(rearX - 0.5, gc + H * 0.25, 0);
    carGroup.add(bed);
  }
  // 跑车尾翼
  if (props.carType === 'sport') {
    const wingGeometry = new THREE.BoxGeometry(0.6, W - 0.2, 0.05);
    const wing = new THREE.Mesh(wingGeometry, metallicMaterial);
    wing.position.set(rearX - 0.4, gc + H * 0.65, 0);
    carGroup.add(wing);
  }
 return carGroup;
};
const initScene = () => {
 const container = containerRef.value;
 if (!container)
 return;
 const width = container.clientWidth;
 const height = container.clientHeight;
 scene = new THREE.Scene();
 scene.background = new THREE.Color(0x0a0a1a);
 camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 100);
 camera.position.set(6, 3, 6);
 camera.lookAt(0, 1, 0);
 renderer = new THREE.WebGLRenderer({ antialias: true });
 renderer.setSize(width, height);
 renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
 renderer.shadowMap.enabled = true;
 renderer.shadowMap.type = THREE.PCFShadowMap;
 container.appendChild(renderer.domElement);
 // 环境光
 const ambientLight = new THREE.AmbientLight(0xffffff, 0.4);
 scene.add(ambientLight);
 // 主方向光（模拟太阳）
 const directionalLight = new THREE.DirectionalLight(0xffffff, 1.0);
 directionalLight.position.set(10, 15, 10);
 directionalLight.castShadow = true;
 directionalLight.shadow.mapSize.width = 2048;
 directionalLight.shadow.mapSize.height = 2048;
 directionalLight.shadow.camera.near = 0.5;
 directionalLight.shadow.camera.far = 50;
 directionalLight.shadow.camera.left = -10;
 directionalLight.shadow.camera.right = 10;
 directionalLight.shadow.camera.top = 10;
 directionalLight.shadow.camera.bottom = -10;
 scene.add(directionalLight);
 // 补光
 const fillLight = new THREE.DirectionalLight(0x88ccff, 0.3);
 fillLight.position.set(-5, 5, -5);
 scene.add(fillLight);
 // 底部反射光
 const bottomLight = new THREE.DirectionalLight(0xffffff, 0.2);
 bottomLight.position.set(0, -5, 0);
 scene.add(bottomLight);
 // 点光源（模拟环境反射）
 const pointLight1 = new THREE.PointLight(0x00d9ff, 0.5, 20);
 pointLight1.position.set(5, 3, 5);
 scene.add(pointLight1);
 const pointLight2 = new THREE.PointLight(0xff6b6b, 0.3, 20);
 pointLight2.position.set(-5, 2, -5);
 scene.add(pointLight2);
 // 地面
 const groundGeometry = new THREE.PlaneGeometry(30, 30);
 const groundMaterial = new THREE.MeshStandardMaterial({
 color: 0x1a1a2e,
 metalness: 0.1,
 roughness: 0.8
 });
 const ground = new THREE.Mesh(groundGeometry, groundMaterial);
 ground.rotation.x = -Math.PI / 2;
 ground.position.y = 0;
 ground.receiveShadow = true;
 scene.add(ground);
 // 网格辅助线
 const gridHelper = new THREE.GridHelper(30, 30, 0x333333, 0x222222);
 gridHelper.position.y = 0.01;
 scene.add(gridHelper);
 // 创建汽车
 carGroup = createCarGeometry();
 scene.add(carGroup);
 // 添加事件监听
 container.addEventListener('mousedown', onMouseDown);
 container.addEventListener('mousemove', onMouseMove);
 container.addEventListener('mouseup', onMouseUp);
 container.addEventListener('mouseleave', onMouseUp);
 container.addEventListener('wheel', onWheel);
 window.addEventListener('resize', onWindowResize);
 // 开始动画
 animate();
};
const onMouseDown = (event) => {
 isDragging = true;
 previousMousePosition = {
 x: event.clientX,
 y: event.clientY
 };
};
const onMouseMove = (event) => {
 if (!isDragging)
 return;
 const deltaX = event.clientX - previousMousePosition.x;
 const deltaY = event.clientY - previousMousePosition.y;
 previousMousePosition = {
 x: event.clientX,
 y: event.clientY
 };
 if (event.button === 2) {
 targetPosition.x += deltaX * 0.01;
 targetPosition.y -= deltaY * 0.01;
 targetPosition.x = Math.max(-5, Math.min(5, targetPosition.x));
 targetPosition.y = Math.max(-3, Math.min(3, targetPosition.y));
 }
 else {
 targetRotation.y += deltaX * 0.01;
 targetRotation.x += deltaY * 0.005;
 targetRotation.x = Math.max(-Math.PI / 3, Math.min(Math.PI / 3, targetRotation.x));
 }
};
const onMouseUp = () => {
 isDragging = false;
};
const onWheel = (event) => {
 event.preventDefault();
 targetDistance += event.deltaY * 0.01;
 targetDistance = Math.max(4, Math.min(15, targetDistance));
};
const onWindowResize = () => {
 const container = containerRef.value;
 if (!container)
 return;
 const width = container.clientWidth;
 const height = container.clientHeight;
 camera.aspect = width / height;
 camera.updateProjectionMatrix();
 renderer.setSize(width, height);
};
const animate = () => {
 animationId = requestAnimationFrame(animate);
 if (autoRotate.value && !isDragging) {
 targetRotation.y += 0.005;
 }
 currentRotation.x += (targetRotation.x - currentRotation.x) * 0.05;
 currentRotation.y += (targetRotation.y - currentRotation.y) * 0.05;
 currentDistance += (targetDistance - currentDistance) * 0.05;
 currentPosition.x += (targetPosition.x - currentPosition.x) * 0.05;
 currentPosition.y += (targetPosition.y - currentPosition.y) * 0.05;
 if (carGroup) {
 carGroup.rotation.x = currentRotation.x;
 carGroup.rotation.y = currentRotation.y;
 }
 camera.position.x = currentPosition.x + Math.sin(currentRotation.y) * currentDistance;
 camera.position.z = Math.cos(currentRotation.y) * currentDistance;
 camera.position.y = currentPosition.y + 3;
 camera.lookAt(currentPosition.x, 1, currentPosition.y);
 renderer.render(scene, camera);
};
const resetView = () => {
 targetRotation = { x: 0.3, y: 0 };
 targetDistance = 8;
 targetPosition = { x: 0, y: 0 };
};
const toggleAutoRotate = () => {
 autoRotate.value = !autoRotate.value;
};
const updateCar = () => {
 if (!scene || !carGroup)
 return;
 scene.remove(carGroup);
 carGroup = createCarGeometry();
 scene.add(carGroup);
};
watch([() => props.carParams, () => props.componentParams, () => props.angleParams, () => props.carType], () => {
 updateCar();
}, { deep: true });
onMounted(() => {
 initScene();
});
onUnmounted(() => {
 if (animationId) {
 cancelAnimationFrame(animationId);
 }
 const container = containerRef.value;
 if (container && renderer) {
 container.removeEventListener('mousedown', onMouseDown);
 container.removeEventListener('mousemove', onMouseMove);
 container.removeEventListener('mouseup', onMouseUp);
 container.removeEventListener('mouseleave', onMouseUp);
 container.removeEventListener('wheel', onWheel);
 window.removeEventListener('resize', onWindowResize);
 renderer.dispose();
 }
});
</script>

<style scoped>
.car-3d-container {
  width: 100%;
  height: 100%;
  position: relative;
  overflow: hidden;
  border-radius: 12px;
}

.controls-overlay {
  position: absolute;
  top: 15px;
  right: 15px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  z-index: 10;
}

.control-btn {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s ease;
  color: rgba(255, 255, 255, 0.7);
}

.control-btn:hover {
  background: rgba(0, 217, 255, 0.3);
  color: #00d9ff;
}

.control-btn.active {
  background: rgba(0, 217, 255, 0.5);
  color: #fff;
}

.info-overlay {
  position: absolute;
  bottom: 15px;
  left: 15px;
  padding: 8px 15px;
  border-radius: 20px;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(10px);
  color: rgba(255, 255, 255, 0.6);
  font-size: 12px;
}
</style>