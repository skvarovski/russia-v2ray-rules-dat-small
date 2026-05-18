# Что это?

Этот репозиторий содержит автоматически обновляемую уменьшенную сборку `geoip.dat` и `geosite.dat` для V2Ray-совместимых клиентов. Файлы собираются из upstream-источников runetfreedom и содержат только категории, перечисленные ниже.

Распространяемые здесь файлы `geoip.dat` и `geosite.dat` могут использоваться в [V2Ray](https://github.com/v2fly/v2ray-core), [v2rayN](https://github.com/2dust/v2rayN), [Xray-core](https://github.com/XTLS/Xray-core), [mihomo](https://github.com/MetaCubeX/mihomo/tree/Meta), [hysteria](https://github.com/apernet/hysteria), [Trojan-Go](https://github.com/p4gefau1t/trojan-go), [leaf](https://github.com/eycorsican/leaf) и так далее.

Репозиторий обновляется каждые 6 часов.

## Какие категории содержатся в файлах

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

- **geoip.dat**
    - [https://raw.githubusercontent.com/skvarovski/russia-v2ray-rules-dat-small/release/geoip.dat](https://raw.githubusercontent.com/skvarovski/russia-v2ray-rules-dat-small/release/geoip.dat)
- **geosite.dat**
    - [https://raw.githubusercontent.com/skvarovski/russia-v2ray-rules-dat-small/release/geosite.dat](https://raw.githubusercontent.com/skvarovski/russia-v2ray-rules-dat-small/release/geosite.dat)

## Upstream-источники

- [@runetfreedom/russia-blocked-geoip](https://github.com/runetfreedom/russia-blocked-geoip) - генерация полного `geoip.dat`
- [@runetfreedom/russia-blocked-geosite](https://github.com/runetfreedom/russia-blocked-geosite) - генерация полного `geosite.dat`
- [@v2fly/domain-list-community](https://github.com/v2fly/domain-list-community) - базовые доменные категории для `geosite.dat`

## Смежные проекты

- [@runetfreedom/russia-v2ray-custom-routing-list](https://github.com/runetfreedom/russia-v2ray-custom-routing-list) - правила маршрутизации для различных клиентов
- [@runetfreedom/geodat2srs](https://github.com/runetfreedom/geodat2srs) - конвертер `geoip.dat`/`geosite.dat` в sing-box srs

## Благодарности

- [antifilter.download](https://antifilter.download/) - за предоставление данных о заблокированных доменах и комьюнити для их обновления
- [re:filter](https://github.com/1andrevich/Re-filter-lists) - за предоставление отфильтрованных данных о заблокированных доменах
- [@Loyalsoldier/v2ray-rules-dat](https://github.com/Loyalsoldier/v2ray-rules-dat) - за идею и основу этого проекта
