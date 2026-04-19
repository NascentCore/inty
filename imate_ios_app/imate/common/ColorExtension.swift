//
//  ColorExtension.swift
//  imate
//
//  Created by 天之行 on 2026/4/19.
//

import SwiftUI

extension Color {
    init(hex: UInt) {
        self.init(
            .sRGB,
            red: Double((hex >> 16) & 0xff) / 255,
            green: Double((hex >> 08) & 0xff) / 255,
            blue: Double((hex >> 00) & 0xff) / 255,
            opacity: Double((hex >> 24) & 0xff) / 255
        )
    }
}
