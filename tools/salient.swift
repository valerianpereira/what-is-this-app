// Prints, for each image given, the box that holds its subject — the union of
// what macOS Vision's objectness saliency picks out — as JSON on stdout:
//   {"path": {"w": 1200, "h": 800, "box": [x, y, w, h]}, ...}
// Coordinates are pixels, origin top-left. A picture Vision finds nothing in
// gets the whole frame as its box. Compile once: swiftc -O tools/salient.swift
import Foundation
import Vision
import ImageIO

var out: [String: Any] = [:]
for path in CommandLine.arguments.dropFirst() {
    let url = URL(fileURLWithPath: path)
    guard let src = CGImageSourceCreateWithURL(url as CFURL, nil),
          let img = CGImageSourceCreateImageAtIndex(src, 0, nil) else {
        FileHandle.standardError.write("cannot read \(path)\n".data(using: .utf8)!)
        continue
    }
    let w = img.width, h = img.height
    let req = VNGenerateObjectnessBasedSaliencyImageRequest()
    let handler = VNImageRequestHandler(cgImage: img, options: [:])
    var box = CGRect(x: 0, y: 0, width: 1, height: 1)
    if (try? handler.perform([req])) != nil,
       let obs = req.results?.first as? VNSaliencyImageObservation,
       let objs = obs.salientObjects, !objs.isEmpty {
        var u = objs[0].boundingBox
        for o in objs.dropFirst() { u = u.union(o.boundingBox) }
        box = u
    }
    // Vision's boxes are normalised with the origin bottom-left
    let x = Int((box.minX * CGFloat(w)).rounded())
    let y = Int(((1 - box.maxY) * CGFloat(h)).rounded())
    out[path] = ["w": w, "h": h,
                 "box": [x, y, Int((box.width * CGFloat(w)).rounded()), Int((box.height * CGFloat(h)).rounded())]]
}
let data = try! JSONSerialization.data(withJSONObject: out, options: [.sortedKeys])
FileHandle.standardOutput.write(data)
FileHandle.standardOutput.write("\n".data(using: .utf8)!)
