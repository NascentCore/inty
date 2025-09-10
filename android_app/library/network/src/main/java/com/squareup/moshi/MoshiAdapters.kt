package com.squareup.moshi

import okio.BufferedSource
import java.lang.reflect.Type
import java.util.concurrent.atomic.AtomicBoolean


class DefaultIfNullFactory : JsonAdapter.Factory {
    override fun create(
        type: Type,
        annotations: MutableSet<out Annotation>,
        moshi: Moshi
    ): JsonAdapter<*>? {
        val delegate = moshi.nextAdapter<Any>(this, type, annotations)
        if (!annotations.isEmpty()) return null
        if (type === Boolean::class.javaPrimitiveType) return delegate
        if (type === Byte::class.javaPrimitiveType) return delegate
        if (type === Char::class.javaPrimitiveType) return delegate
        if (type === Double::class.javaPrimitiveType) return delegate
        if (type === Float::class.javaPrimitiveType) return delegate
        if (type === Int::class.javaPrimitiveType) return delegate
        if (type === Long::class.javaPrimitiveType) return delegate
        if (type === Short::class.javaPrimitiveType) return delegate
        if (type === Boolean::class.java) return delegate
        if (type === Byte::class.java) return delegate
        if (type === Char::class.java) return delegate
        if (type === Double::class.java) return delegate
        if (type === Float::class.java) return delegate
        if (type === Int::class.java) return delegate
        if (type === Long::class.java) return delegate
        if (type === Short::class.java) return delegate
        if (type === String::class.java) return delegate
        return object : JsonAdapter<Any>() {
            override fun fromJson(reader: JsonReader): Any? {
                return if (reader.peek() == JsonReader.Token.BEGIN_OBJECT) {
                    delegate.fromJson(JsonReaderSkipNullValuesWrapper(reader))
                } else {
                    delegate.fromJson(reader)
                }
            }

            override fun toJson(writer: JsonWriter, value: Any?) {
                return delegate.toJson(writer, value)
            }
        }
    }
}

class JsonReaderSkipNullValuesWrapper(
    private val wrapped: JsonReader
) : JsonReader() {
    private var ignoreSkipName = AtomicBoolean(false)
    private var ignoreSkipValue = AtomicBoolean(false)
    override fun close() {
        wrapped.close()
    }

    override fun beginArray() {
        wrapped.beginArray()
    }

    override fun endArray() {
        wrapped.endArray()
    }

    override fun beginObject() {
        wrapped.beginObject()
    }

    override fun endObject() {
        wrapped.endObject()
        ignoreSkipName.compareAndSet(true, false)
        ignoreSkipValue.compareAndSet(true, false)
    }

    override fun hasNext(): Boolean {
        return wrapped.hasNext()
    }

    override fun peek(): Token {
        return wrapped.peek()
    }

    override fun nextName(): String {
        return wrapped.nextName()
    }

    override fun selectName(options: Options): Int {
        val index = wrapped.selectName(options)
        return if (index >= 0 && wrapped.peek() == Token.NULL) {
            wrapped.skipValue()
            ignoreSkipName.set(true)
            ignoreSkipValue.set(true)
            -1
        } else {
            index
        }
    }

    override fun skipName() {
        if (ignoreSkipName.compareAndSet(true, false)) {
            return
        }
        wrapped.skipName()
    }

    override fun nextString(): String {
        return wrapped.nextString()
    }

    override fun selectString(options: Options): Int {
        return wrapped.selectString(options)
    }

    override fun nextBoolean(): Boolean {
        return wrapped.nextBoolean()
    }

    override fun <T : Any?> nextNull(): T? {
        return wrapped.nextNull()
    }

    override fun nextDouble(): Double {
        return wrapped.nextDouble()
    }

    override fun nextLong(): Long {
        return wrapped.nextLong()
    }

    override fun nextInt(): Int {
        return wrapped.nextInt()
    }

    override fun nextSource(): BufferedSource {
        return wrapped.nextSource()
    }

    override fun skipValue() {
        if (ignoreSkipValue.compareAndSet(true, false)) {
            return
        }
        wrapped.skipValue()
    }

    override fun peekJson(): JsonReader {
        return wrapped.peekJson()
    }

    override fun promoteNameToValue() {
        wrapped.promoteNameToValue()
    }
}
