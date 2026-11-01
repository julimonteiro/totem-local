import Cocoa
import SwiftUI
import CoreBluetooth

struct LiveLayer { let label: String; let bindings: [String] }

final class LiveModel: NSObject, ObservableObject, URLSessionDataDelegate, CBCentralManagerDelegate, CBPeripheralDelegate {
    @Published var layers: [LiveLayer] = []
    @Published var activeLayer = 0
    @Published var pressed: Set<Int> = []
    @Published var leftBattery = "—"
    @Published var rightBattery = "—"
    @Published var transport = "Aguardando TOTEM"
    @Published var produced = "—"
    @Published var live = false
    @Published var bluetoothStatus = "Bluetooth"
    @Published var batteryNotice = ""
    var onUpdate: (([String:Any]) -> Void)?
    var token = ""
    var firmware = ""
    var buffer = Data()
    var stream: URLSessionDataTask?
    var session: URLSession!
    var central: CBCentralManager?
    var peripheral: CBPeripheral?
    var scanTimeout: DispatchWorkItem?
    var telemetryReady = false
    let base = "http://127.0.0.1:8767"
    let stateUUID = CBUUID(string: "5fbc1001-6c8d-4f43-a01a-a6d18a88c001")
    let outputUUID = CBUUID(string: "5fbc1002-6c8d-4f43-a01a-a6d18a88c001")

    func start() { loadState(); connectStream() }
    func loadState() {
        URLSession.shared.dataTask(with: URL(string: base + "/api/state")!) { data,_,_ in
            guard let data=data, let object=try? JSONSerialization.jsonObject(with:data) as? [String:Any] else { return }
            DispatchQueue.main.async {
                self.token=object["token"] as? String ?? ""
                let telemetry = object["telemetry"] as? [String:Any] ?? [:]
                let sideData = telemetry["sides"] as? [String:[String:Any]] ?? [:]
                let mapMatches = (object["runtime_build"] as? String) == (sideData["left"]?["build"] as? String)
                if mapMatches, let values=object["runtime_layers"] as? [[String:Any]] {
                    self.layers=values.map { LiveLayer(label:$0["label"] as? String ?? "",bindings:$0["bindings"] as? [String] ?? []) }
                } else { self.layers=[] }
                if let telemetry=object["telemetry"] as? [String:Any] { self.update(telemetry) }
            }
        }.resume()
    }
    func connectStream() {
        let config=URLSessionConfiguration.ephemeral
        config.timeoutIntervalForRequest=60
        session=URLSession(configuration:config,delegate:self,delegateQueue:OperationQueue())
        stream=session.dataTask(with:URL(string:base+"/api/events")!); stream?.resume()
    }
    func urlSession(_ session: URLSession, dataTask: URLSessionDataTask, didReceive data: Data) {
        buffer.append(data)
        let delimiter=Data("\n\n".utf8)
        while let range=buffer.range(of:delimiter) {
            let chunk=buffer[..<range.lowerBound]; buffer.removeSubrange(..<range.upperBound)
            guard let text=String(data:chunk,encoding:.utf8),text.hasPrefix("data: "),let json=text.dropFirst(6).data(using:.utf8),let object=try? JSONSerialization.jsonObject(with:json) as? [String:Any] else { continue }
            DispatchQueue.main.async { self.update(object) }
        }
    }
    func urlSession(_ session: URLSession, task: URLSessionTask, didCompleteWithError error: Error?) {
        DispatchQueue.main.async {
            self.live=false; self.pressed=[]; self.transport="Serviço desconectado"
            self.layers=[]; self.leftBattery="—"; self.rightBattery="—"
            self.onUpdate?([:])
            DispatchQueue.main.asyncAfter(deadline:.now()+1) { self.buffer=Data(); self.loadState(); self.connectStream() }
        }
    }
    func update(_ data: [String:Any]) {
        let sides=data["sides"] as? [String:[String:Any]] ?? [:]
        let left=sides["left"] ?? [:], right=sides["right"] ?? [:]
        func number(_ d:[String:Any],_ k:String)->Int { (d[k] as? NSNumber)?.intValue ?? -1 }
        func battery(_ d:[String:Any])->String { (d["fresh"] as? Bool == true && number(d,"battery")>=0) ? "\(number(d,"battery"))%" : "—" }
        leftBattery=battery(left); rightBattery=battery(right)
        live=left["fresh"] as? Bool ?? false
        let id=left["build"] as? String ?? ""
        if id != firmware { firmware=id; layers=[]; loadState() }
        activeLayer=number(left,"layer")
        transport=live ? (number(left,"endpoint")==1 ? "Bluetooth" : "USB") : "Aguardando TOTEM"
        pressed=Set((data["pressed"] as? [Int] ?? [])+(data["flashes"] as? [Int] ?? []))
        if let output=data["produced"] as? [String:Any],let label=output["label"] as? String { produced=label }
        onUpdate?(data)
    }
    var layerName: String { activeLayer>=0 && activeLayer<layers.count ? layers[activeLayer].label : "—" }
    func binding(_ position:Int)->String? { guard activeLayer>=0,activeLayer<layers.count,position<layers[activeLayer].bindings.count else { return nil }; return layers[activeLayer].bindings[position] }
    func send(_ object:[String:Any]) {
        guard !token.isEmpty else { return }
        var request=URLRequest(url:URL(string:base+"/api/native")!)
        request.httpMethod="POST"; request.setValue("application/json",forHTTPHeaderField:"Content-Type"); request.setValue(token,forHTTPHeaderField:"X-Totem-Token")
        request.httpBody=try? JSONSerialization.data(withJSONObject:object)
        URLSession.shared.dataTask(with:request).resume()
    }
    func readableBluetoothError(_ error: Error) -> String {
        let value = error as NSError
        if value.domain == "CBATTErrorDomain" && [5,15].contains(value.code) {
            return "Pareamento não autenticado. Esqueça o TOTEM no macOS, limpe o perfil no teclado e emparelhe novamente."
        }
        return error.localizedDescription
    }
    func status(_ message:String) { bluetoothStatus=message; send(["status":message]) }
    func connectBluetooth() {
        telemetryReady = false
        status("Procurando TOTEM…")
        if central == nil { central=CBCentralManager(delegate:self,queue:.main) }
        else { beginScan() }
    }
    func centralManagerDidUpdateState(_ central: CBCentralManager) {
        if central.state == .poweredOn { beginScan() }
        else if central.state == .unauthorized { status("Permita Bluetooth para TOTEM Local nos Ajustes do Sistema.") }
        else { status("Bluetooth indisponível") }
    }
    func beginScan() {
        guard let central=central,central.state == .poweredOn else { return }
        let connected = central.retrieveConnectedPeripherals(withServices: [CBUUID(string: "1812")]).filter { ($0.name ?? "").uppercased().contains("TOTEM") }
        if connected.count == 1 {
            self.peripheral = connected[0]
            connected[0].delegate = self
            central.connect(connected[0])
            return
        }
        central.scanForPeripherals(withServices:nil)
        scanTimeout?.cancel()
        let timeout=DispatchWorkItem { [weak self] in self?.central?.stopScan(); if self?.peripheral?.state != .connected { self?.status("TOTEM não encontrado; confira o perfil Bluetooth.") } }
        scanTimeout=timeout; DispatchQueue.main.asyncAfter(deadline:.now()+12,execute:timeout)
    }
    func centralManager(_ central:CBCentralManager,didDiscover peripheral:CBPeripheral,advertisementData:[String:Any],rssi RSSI:NSNumber) {
        let name=peripheral.name ?? advertisementData[CBAdvertisementDataLocalNameKey] as? String ?? ""
        guard name.uppercased().contains("TOTEM") else { return }
        central.stopScan(); scanTimeout?.cancel(); self.peripheral=peripheral; peripheral.delegate=self
        status("Conectando ao TOTEM…"); central.connect(peripheral)
    }
    func centralManager(_ central:CBCentralManager,didConnect peripheral:CBPeripheral) { peripheral.discoverServices(nil) }
    func centralManager(_ central:CBCentralManager,didFailToConnect peripheral:CBPeripheral,error:Error?) { status("Falha na conexão Bluetooth") }
    func centralManager(_ central:CBCentralManager,didDisconnectPeripheral peripheral:CBPeripheral,error:Error?) { telemetryReady=false; status("Bluetooth desconectado") }
    func peripheral(_ peripheral:CBPeripheral,didDiscoverServices error:Error?) {
        for service in peripheral.services ?? [] { peripheral.discoverCharacteristics([stateUUID,outputUUID],for:service) }
    }
    func peripheral(_ peripheral:CBPeripheral,didDiscoverCharacteristicsFor service:CBService,error:Error?) {
        for characteristic in service.characteristics ?? [] {
            if characteristic.uuid==stateUUID || characteristic.uuid==outputUUID {
                peripheral.setNotifyValue(true,for:characteristic)
                if characteristic.uuid==stateUUID { peripheral.readValue(for:characteristic) }
            }
        }
    }
    func peripheral(_ peripheral:CBPeripheral,didUpdateNotificationStateFor characteristic:CBCharacteristic,error:Error?) {
        if let error=error { status(readableBluetoothError(error)) } else if characteristic.isNotifying && !telemetryReady { status("Validando dados do TOTEM…") }
    }
    func peripheral(_ peripheral:CBPeripheral,didUpdateValueFor characteristic:CBCharacteristic,error:Error?) {
        guard error==nil,let data=characteristic.value else { if let error=error { status(readableBluetoothError(error)) }; return }
        if characteristic.uuid==stateUUID { if !telemetryReady { telemetryReady=true; status("Bluetooth conectado") }; send(["packet":Array(data)]) }
        else if characteristic.uuid==outputUUID { send(["output":Array(data)]) }
    }
}

func nativeKey(_ code:String)->String {
    let aliases=["SPACE":"Espaço","SPC":"Espaço","ENTER":"↩","RET":"↩","BSPC":"⌫","BACKSPACE":"⌫","TAB":"⇥","ESC":"⎋","DELETE":"⌦","DEL":"⌦","LCMD":"⌘","LGUI":"⌘","LCTRL":"⌃","RCTRL":"⌃","LALT":"⌥","RALT":"⌥","LSHIFT":"⇧","LSHFT":"⇧","RSHFT":"⇧","LEFT_SHIFT":"⇧","RSHIFT":"⇧","LEFT":"←","RIGHT":"→","UP":"↑","DOWN":"↓","LEFT_ARROW":"←","RIGHT_ARROW":"→","UP_ARROW":"↑","DOWN_ARROW":"↓","FSLH":"/","SLASH":"/","COMMA":",","DOT":".","PERIOD":".","SEMI":";","SQT":"'","MINUS":"−","EQUAL":"=","PLUS":"+","BSLH":"\\","C_VOL_UP":"Vol +","C_VOL_DN":"Vol −","C_PP":"⏯","C_MUTE":"Mudo","GRAVE":"`"]
    if let alias=aliases[code] { return alias }
    for (prefix,symbol) in [("LC(","⌃"),("LS(","⇧"),("LA(","⌥"),("LG(","⌘"),("RA(","⌥")] { if code.hasPrefix(prefix),code.hasSuffix(")") { return symbol+nativeKey(String(code.dropFirst(3).dropLast())) } }
    if code.range(of:"^(N|NUMBER_)[0-9]$",options:.regularExpression) != nil { return String(code.suffix(1)) }
    return code
}
func nativeBinding(_ binding:String?)->(String,String) {
    guard let binding=binding else { return ("?","") }
    let p=binding.split(separator:" ").map(String.init)
    guard let action=p.first else { return ("?","") }
    if action=="&kp" { return (nativeKey(p.dropFirst().joined(separator:" ")),"") }
    if action=="&trans" { return ("↓","inferior") }
    if action=="&none" { return ("—","") }
    if action.hasPrefix("&mt"),p.count>=3 { return (nativeKey(p[2]),nativeKey(p[1])) }
    if action=="&lt",p.count>=3 { return (nativeKey(p[2]),"↗ "+p[1]) }
    if action=="&mo",p.count>=2 { return (p[1]=="1" ? "NAV" : "Ajustes","segure") }
    if action=="&bt",p.count>=2 {
        if p[1]=="BT_SEL",p.count>=3 { return ("BT \((Int(p[2]) ?? 0)+1)","perfil") }
        if p[1]=="BT_CLR" { return ("Limpar BT","perfil atual") }
    }
    if action=="&out",p.count>=2 { return (p[1]=="OUT_USB" ? "USB" : p[1]=="OUT_BLE" ? "Bluetooth" : "Alternar","saída") }
    return (String(action.dropFirst()),p.dropFirst().joined(separator:" "))
}

struct KeyPosition: Identifiable { let id:Int; let column:Int; let row:Int }
func halfPositions(_ right:Bool)->[KeyPosition] {
    var values:[KeyPosition]=[]
    for c in 0..<5 {
        values.append(KeyPosition(id:(right ? 5:0)+c,column:c+(right ? 0:1),row:0))
        values.append(KeyPosition(id:(right ? 15:10)+c,column:c+(right ? 0:1),row:1))
        values.append(KeyPosition(id:(right ? 26:21)+c,column:c+(right ? 0:1),row:2))
    }
    values.append(KeyPosition(id:right ? 31:20,column:right ? 5:0,row:2))
    for c in 0..<3 { values.append(KeyPosition(id:(right ? 35:32)+c,column:c+(right ? 0:3),row:3)) }
    return values
}
struct NativeHalf: View {
    @ObservedObject var model:LiveModel
    let right:Bool
    var body: some View {
        GeometryReader { geometry in
            let pitch=geometry.size.width/6
            ZStack(alignment:.topLeading) {
                ForEach(halfPositions(right)) { key in
                    let labels=nativeBinding(model.binding(key.id))
                    let on=model.pressed.contains(key.id)
                    let col=right ? 5-key.column : key.column
                    let offsets:[CGFloat]=[10,11,3,0,3,9]
                    VStack(spacing:2) {
                        Text(labels.0).font(.system(size:12,weight:.medium,design:.rounded)).lineLimit(1).minimumScaleFactor(0.65)
                        if !labels.1.isEmpty { Text(labels.1).font(.system(size:8)).foregroundStyle(on ? Color.white.opacity(0.85) : Color.secondary).lineLimit(1) }
                    }
                    .foregroundStyle(on ? Color.white : Color.primary)
                    .frame(width:pitch-5,height:39)
                    .background(on ? Color.accentColor : Color.primary.opacity(0.065),in:RoundedRectangle(cornerRadius:7))
                    .overlay(RoundedRectangle(cornerRadius:7).strokeBorder(Color.primary.opacity(on ? 0:0.09),lineWidth:0.5))
                    .position(x:(CGFloat(key.column)+0.5)*pitch,y:CGFloat(key.row)*44+23+(key.row==3 ? 12:offsets[col]))
                }
            }
        }.frame(height:195)
    }
}
struct NativeOverlay: View {
    @ObservedObject var model:LiveModel
    var body: some View {
        VStack(spacing:13) {
            HStack(spacing:18) {
                Label("TOTEM",systemImage:"keyboard").font(.system(size:12,weight:.semibold))
                Spacer()
                Label("E \(model.leftBattery)",systemImage:"battery.75percent")
                Label("D \(model.rightBattery)",systemImage:"battery.75percent")
                Divider().frame(height:14)
                Label(model.transport,systemImage:model.transport=="USB" ? "cable.connector":"antenna.radiowaves.left.and.right")
                Text(model.layerName).fontWeight(.semibold).padding(.horizontal,8).padding(.vertical,4).background(.quaternary,in:Capsule())
                Button { model.connectBluetooth() } label: { Image(systemName:"antenna.radiowaves.left.and.right") }.buttonStyle(.borderless).help(model.bluetoothStatus)
            }.font(.system(size:11)).foregroundStyle(.secondary)
            HStack(spacing:25) { NativeHalf(model:model,right:false); NativeHalf(model:model,right:true) }
            HStack(spacing:12) {
                Image(systemName:"arrow.turn.down.right").foregroundStyle(.tertiary)
                VStack(alignment:.leading,spacing:3) {
                    Text("SAÍDA PRODUZIDA").font(.system(size:9,weight:.medium)).foregroundStyle(.secondary)
                    Text(model.produced).font(.system(size:22,weight:.medium,design:.monospaced)).lineLimit(1)
                }
                Spacer()
                VStack(alignment:.trailing,spacing:4) {
                    Label(model.live ? "Ao vivo":"Aguardando dados",systemImage:model.live ? "circle.fill":"circle").font(.system(size:10)).foregroundStyle(model.live ? Color.green:Color.secondary)
                    Text("Saída ZMK · composição de texto pelo macOS").font(.system(size:8)).foregroundStyle(.tertiary)
                }
            }.padding(12).background(.quaternary.opacity(0.5),in:RoundedRectangle(cornerRadius:10))
            if !model.batteryNotice.isEmpty { Text(model.batteryNotice).font(.caption).foregroundStyle(.orange) }
        }.padding(18).background(.regularMaterial)
    }
}
