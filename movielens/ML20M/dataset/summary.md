# Summary of ml-20m

## Entities

- item (27.3 k, 4 attributes)
- user (138 k, 0 attributes)

### Entity `item`

- 27,278 instances

#### Attributes

| Name       | Layout |  Type  | Dimension |  Count |      Size |
| :----------| :----: | :----: |---------: |------: |---------: |
| title      | scalar | string |         - | 27,278 | 851.3 KiB |
| genres     |  list  | string |         - | 27,278 | 666.1 KiB |
| tag_counts | sparse | int64  |    38,643 | 19,545 |   3.2 MiB |
| tag_genome | vector | float  |     1,128 | 10,381 |  44.8 MiB |

#### Schema

```
item_id: int32
title: string
genres: list<item: string>
  child 0, item: string
tag_counts: list<item: struct<index: int64, value: int64>>
  child 0, item: struct<index: int64, value: int64>
      child 0, index: int64
      child 1, value: int64
tag_genome: list<item: float>
  child 0, item: float
  -- field metadata --
  lenskit:names: '["007", "007 (series)", "18th century", "1920s", "1930s' + 15760
```

### Entity `user`

- 138,493 instances

#### Schema

```
user_id: int32
```

## Relationships

- rating (20.0 M, 2 attributes, interaction)

### Relationship `rating`

- 20,000,263 records

#### Entities

| Name | Class | Unique Count |
| :----| :---: |------------: |
| user |  user |      138,493 |
| item |  item |       26,744 |

#### Attributes

| Name      | Layout |      Type     | Dimension |      Count |      Size |
| :---------| :----: | :-----------: |---------: |----------: |---------: |
| rating    | scalar |     float     |         - | 20,000,263 |  76.3 MiB |
| timestamp | scalar | timestamp[ns] |         - | 20,000,263 | 152.6 MiB |

## Data Tables

| Name   |       Rows |     Bytes |
| :------|----------: |---------: |
| item   |     27,278 |  49.5 MiB |
| rating | 20,000,263 | 386.2 MiB |
| user   |    138,493 | 541.0 KiB |
