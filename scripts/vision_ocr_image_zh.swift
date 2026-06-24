import Foundation
import Vision

if CommandLine.arguments.count < 2 {
    fputs("usage: swift vision_ocr_image_zh.swift image.png [image2.png ...]\n", stderr)
    exit(2)
}

for imagePath in CommandLine.arguments.dropFirst() {
    let imageURL = URL(fileURLWithPath: imagePath)
    guard FileManager.default.fileExists(atPath: imageURL.path) else {
        fputs("cannot read image: \(imageURL.path)\n", stderr)
        continue
    }

    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.recognitionLanguages = ["zh-Hans", "en-US"]
    request.usesLanguageCorrection = false
    let handler = VNImageRequestHandler(url: imageURL, options: [:])
    do {
        try handler.perform([request])
    } catch {
        fputs("vision recognition failed for \(imageURL.path): \(error)\n", stderr)
        continue
    }

    let observations = request.results ?? []
    for observation in observations.sorted(by: {
        if abs($0.boundingBox.midY - $1.boundingBox.midY) > 0.01 {
            return $0.boundingBox.midY > $1.boundingBox.midY
        }
        return $0.boundingBox.minX < $1.boundingBox.minX
    }) {
        guard let text = observation.topCandidates(1).first else { continue }
        let box = observation.boundingBox
        print(String(format: "%@\t%.6f\t%.6f\t%.6f\t%.6f\t%@",
                     imageURL.path, box.minX, box.minY, box.width, box.height, text.string))
    }
}
