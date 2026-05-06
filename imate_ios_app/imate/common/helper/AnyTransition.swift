//
//  AnyTransition.swift
//  imate
//
//  Created by 天之行 on 2026/5/6.
//

import SwiftUI

extension AnyTransition {

    static var chatBubble: AnyTransition {
        .asymmetric(
            insertion: .modifier(
                active: BubbleModifier(offsetY: 20, opacity: 0),
                identity: BubbleModifier(offsetY: 0, opacity: 1)
            ),
            removal: .opacity
        )
    }
}

struct BubbleModifier: ViewModifier {

    let offsetY: CGFloat
    let opacity: Double

    func body(content: Content) -> some View {
        content
            .offset(y: offsetY)
            .opacity(opacity)
    }
}
