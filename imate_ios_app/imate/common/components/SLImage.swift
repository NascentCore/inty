//
//  SLImage.swift
//  imate
//
//  Created by 天之行 on 2026/5/7.
//

import Kingfisher
import SwiftUI

enum SLImageSource {
    case network(String)
    case local(String)
}

struct SLImage: View {

    let source: SLImageSource

    var width: CGFloat? = nil
    var height: CGFloat? = nil

    var contentMode: SwiftUI.ContentMode = .fill

    var body: some View {

        Group {

            switch source {

            case .network(let url):
                KFImage(URL(string: url))
                    .placeholder {
                        placeholderView
                    }
                    .retry(maxCount: 2, interval: .seconds(2))
                    .fade(duration: 0.25)
                    .resizable()

            case .local(let name):

                Image(name)
                    .resizable()
            }
        }
        .aspectRatio(contentMode: contentMode)
        .frame(width: width, height: height)
        .clipped()
    }

    private var placeholderView: some View {

        ZStack {

            Color.gray.opacity(0.1)

            Image(systemName: "photo")
                .foregroundColor(.gray)
        }
    }
}
