# Что это?

Этот репозиторий содержит автоматически обновляемые сборки `geoip.dat` и `geosite.dat` для V2Ray-совместимых клиентов. Файлы собираются из первичных текстовых источников, а не из готовых upstream `.dat` артефактов.

Распространяемые здесь файлы `geoip.dat` и `geosite.dat` могут использоваться в [V2Ray](https://github.com/v2fly/v2ray-core), [v2rayN](https://github.com/2dust/v2rayN), [Xray-core](https://github.com/XTLS/Xray-core), [mihomo](https://github.com/MetaCubeX/mihomo/tree/Meta), [hysteria](https://github.com/apernet/hysteria), [Trojan-Go](https://github.com/p4gefau1t/trojan-go), [leaf](https://github.com/eycorsican/leaf) и так далее.

Репозиторий обновляется каждые 6 часов.

## Какие варианты собираются

- `internal` - российский direct-набор. Корневые `geoip.dat` и `geosite.dat` в ветке `release` теперь указывают именно на этот вариант.
- `small` - уменьшенный proxy/direct/block-набор, который раньше публиковался в корне.
- `full` - полный локально собранный набор исходных категорий.

## Какие категории содержатся в small

### geoip.dat

В уменьшенную сборку включены:

- `geoip:ru-blocked`
- `geoip:re-filter`
- `geoip:ru-blocked-community`
- `geoip:telegram`
- `geoip:google`
- `geoip:cloudflare`
- `geoip:ru`
- `geoip:ru-whitelist`
- `geoip:yandex`
- `geoip:ddos-guard`
- `geoip:private`

### geosite.dat

В уменьшенную сборку включены:

- `geosite:ru-blocked`
- `geosite:antifilter-download-community`
- `geosite:category-media`
- `geosite:category-communication`
- `geosite:category-social-media-!cn`
- `geosite:category-entertainment`
- `geosite:category-games`
- `geosite:category-dev`
- `geosite:category-forums`
- `geosite:category-ai-!cn`
- `geosite:category-anticensorship`
- `geosite:category-vpnservices`
- `geosite:category-cryptocurrency`
- `geosite:category-scholar-!cn`
- `geosite:category-cdn-!cn`
- `geosite:google`
- `geosite:cloudflare`
- `geosite:amazon`
- `geosite:category-ru`
- `geosite:ru-available-only-inside`
- `geosite:category-bank-ru`
- `geosite:category-gov-ru`
- `geosite:private`
- `geosite:category-ads-all`

# Скачать

По ссылкам ниже всегда доступна последняя версия файлов из ветки `release`.

Корневые ссылки возвращают `internal`:

- **geoip.dat**
    - [https://raw.githubusercontent.com/skvarovski/russia-v2ray-rules-dat-small/release/geoip.dat](https://raw.githubusercontent.com/skvarovski/russia-v2ray-rules-dat-small/release/geoip.dat)
- **geosite.dat**
    - [https://raw.githubusercontent.com/skvarovski/russia-v2ray-rules-dat-small/release/geosite.dat](https://raw.githubusercontent.com/skvarovski/russia-v2ray-rules-dat-small/release/geosite.dat)

Явные варианты:

- **internal**
    - [https://raw.githubusercontent.com/skvarovski/russia-v2ray-rules-dat-small/release/internal/geoip.dat](https://raw.githubusercontent.com/skvarovski/russia-v2ray-rules-dat-small/release/internal/geoip.dat)
    - [https://raw.githubusercontent.com/skvarovski/russia-v2ray-rules-dat-small/release/internal/geosite.dat](https://raw.githubusercontent.com/skvarovski/russia-v2ray-rules-dat-small/release/internal/geosite.dat)
- **small**
    - [https://raw.githubusercontent.com/skvarovski/russia-v2ray-rules-dat-small/release/small/geoip.dat](https://raw.githubusercontent.com/skvarovski/russia-v2ray-rules-dat-small/release/small/geoip.dat)
    - [https://raw.githubusercontent.com/skvarovski/russia-v2ray-rules-dat-small/release/small/geosite.dat](https://raw.githubusercontent.com/skvarovski/russia-v2ray-rules-dat-small/release/small/geosite.dat)
- **full**
    - [https://raw.githubusercontent.com/skvarovski/russia-v2ray-rules-dat-small/release/full/geoip.dat](https://raw.githubusercontent.com/skvarovski/russia-v2ray-rules-dat-small/release/full/geoip.dat)
    - [https://raw.githubusercontent.com/skvarovski/russia-v2ray-rules-dat-small/release/full/geosite.dat](https://raw.githubusercontent.com/skvarovski/russia-v2ray-rules-dat-small/release/full/geosite.dat)

## Источники

- [antifilter.download](https://antifilter.download/) - IP и домены заблокированных ресурсов
- [community.antifilter.download](https://community.antifilter.download/) - community-списки заблокированных ресурсов
- [re:filter](https://github.com/1andrevich/Re-filter-lists) - отфильтрованные IP и домены заблокированных ресурсов
- [@v2fly/domain-list-community](https://github.com/v2fly/domain-list-community) - базовые доменные категории для `geosite.dat`
- [@Loyalsoldier/geoip](https://github.com/Loyalsoldier/geoip) - базовые IP-категории

## Смежные проекты

- [@runetfreedom/russia-v2ray-custom-routing-list](https://github.com/runetfreedom/russia-v2ray-custom-routing-list) - правила маршрутизации для различных клиентов
- [@runetfreedom/geodat2srs](https://github.com/runetfreedom/geodat2srs) - конвертер `geoip.dat`/`geosite.dat` в sing-box srs

## Благодарности

- [antifilter.download](https://antifilter.download/) - за предоставление данных о заблокированных доменах и комьюнити для их обновления
- [re:filter](https://github.com/1andrevich/Re-filter-lists) - за предоставление отфильтрованных данных о заблокированных доменах
- [@Loyalsoldier/v2ray-rules-dat](https://github.com/Loyalsoldier/v2ray-rules-dat) - за идею и основу этого проекта
