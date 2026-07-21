package require models
package require runs

source category.tcl

set ::valid_sample_size 10000

# Crafts: Arts_Crafts_and_Sewing
# Auto: Automotive
# Baby: Baby_Products
# Beauty: Beauty_and_Personal_Care
# Books: Books
azcat -no-tune CDV CDs_and_Vinyl
# Cell: Cell_Phones_and_Accessories
# Clothing: Clothing_Shoes_and_Jewelry
# Elec: Electronics
# Grocery: Grocery_and_Gourmet_Food
# HealthHouse: Health_and_Household
# HomeKitchen: Home_and_Kitchen
# IndSci: Industrial_and_Scientific
# Kindle: Kindle_Store
# MovTV: Movies_and_TV
azcat -no-tune MusInst Musical_Instruments
# Office: Office_Products
# PLG: Patio_Lawn_and_Garden
azcat -no-tune Pet Pet_Supplies
azcat -no-tune Software Software
# Sports: Sports_and_Outdoors
# THI: Tools_and_Home_Improvement
# Toys: Toys_and_Games
# VidGames: Video_Games

stage collect-stats {
    cmd lenskit codex sql -f bench-stats.sql stats.duckdb
    out stats.duckdb
    dep bench-stats.sql
    dep {*}[glob data/*.csv.gz]
}
