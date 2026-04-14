// swift-tools-version: 6.1
// The swift-tools-version declares the minimum version of Swift required to build this package.

import PackageDescription

let package = Package(
    name: "Networking",
    platforms: [.iOS(.v18)],
    products: [
        .library(
            name: "Networking",
            targets: ["Networking"]
        )
    ],
    dependencies: [
        .package(url: "https://github.com/theosementa/NetworkKit", branch: "1.0.4")
    ],
    targets: [
        .target(
            name: "Networking",
            dependencies: [
                .product(name: "NetworkKit", package: "NetworkKit")
            ]
        )
    ],
    swiftLanguageModes: [.v6]
)
