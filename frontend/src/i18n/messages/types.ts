import type zhHans from './zh-Hans/index'

/** Widen zh-Hans literal strings so en/zh-Hant catalogs type-check. */
type DeepString<T> = T extends string
  ? string
  : T extends readonly (infer U)[]
    ? readonly DeepString<U>[]
    : T extends object
      ? { readonly [K in keyof T]: DeepString<T[K]> }
      : T

export type Messages = DeepString<typeof zhHans>
