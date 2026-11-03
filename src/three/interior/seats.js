import {
  createSeatRow,
  createInteriorTrim,
  createIpConsole,
  createLuggageTrim
} from '../../utils/carInterior.js'

/**
 * 内饰座椅与舱内附件（P2 拆分：原 Car3D.vue 的 addInteriorSeats + attachDoorTrimToHinges）
 *
 * 只做装配，不做推导：座椅布局/内饰坐标全部来自 carInterior（与 2D 同一真源）；
 * carType 对应的座椅材质预设由调用方 resolveSeatPreset 算好后传入，模块不读 props；
 * 门铰链由调用方注入（禁止横向 import Car3D 或 doors），空数组时保持原位挂载。
 *
 * 调用时序是契约：必须在 createDoorRig 之后执行，否则门板内饰拿不到铰链引用，
 * 开门时会留在原位（cockpit 分镜立刻可见错位）。
 */

/**
 * 门板内饰 + 扶手重挂到对应车门铰链。
 *
 * createInteriorTrim 产出的是世界坐标网格（BoxGeometry 居中、position = AABB 中心），
 * 这里把 position 减去铰链轴（x / z，铰链 y=0），再挂为铰链子节点：
 * 之后与门板/门玻璃同轴同角度旋转 → 开门时门板内饰与扶手随门一同摆出。
 * 按网格名 `door-{trim|armrest}-{front|rear}-{left|right}` 与 doorHinges 的 { key, sign } 配对。
 * NURBS 路径无门铰链（doorHinges 为空）→ 保持原位挂载，因此本函数必须早退而不是报错。
 *
 * @param {THREE.Object3D} trimGroup
 * @param {Array<{key:string, sign:number, hinge:THREE.Object3D}>} doorHinges 调用方注入
 */
export function attachDoorTrimToHinges(trimGroup, doorHinges = []) {
  if (!doorHinges.length) return
  // 遍历快照：reparent 会从 trimGroup 摘除子节点并改写 children
  for (const mesh of [...trimGroup.children]) {
    const m = /^door-(trim|armrest)-(front|rear)-(left|right)$/.exec(mesh.name)
    if (!m) continue
    const key = m[2]
    const sign = m[3] === 'left' ? -1 : 1
    const target = doorHinges.find((d) => d.key === key && d.sign === sign)
    if (!target) continue
    mesh.position.x -= target.hinge.position.x
    mesh.position.z -= target.hinge.position.z
    target.hinge.add(mesh)
  }
}

/**
 * 按 carProfile 座椅布局逐排生成内饰座椅并挂入父级（挤出路径与 NURBS 路径共用）。
 *
 * @param {THREE.Object3D} parent  挤出路径传 group、NURBS 路径传 root，签名不硬编码
 * @param {object} P               deriveCarProfile 结果
 * @param {string} preset          resolveSeatPreset 结果（材质变体）
 * @param {Array} doorHinges       门铰链引用；NURBS 路径为空数组 → 内饰原位挂载
 */
export function addInteriorSeats({ parent, P, preset, doorHinges = [] }) {
  for (let row = 1; row <= (P.seatRows || 1); row++) {
    parent.add(createSeatRow(P, row, { materialVariant: preset }))
  }
  // 其余内饰件（门板内饰 / 中央通道 / 顶棚 / 地毯 / 安全带固定点）与座椅同一父级、同一坐标源
  const trim = createInteriorTrim(P)
  parent.add(trim)
  attachDoorTrimToHinges(trim, doorHinges)
  // IP/CONSOLE 功能模块 + 前/后行李舱内饰（deriveIpConsoleLayout / deriveLuggageLayout 同一真源）
  parent.add(createIpConsole(P))
  parent.add(createLuggageTrim(P))
}
