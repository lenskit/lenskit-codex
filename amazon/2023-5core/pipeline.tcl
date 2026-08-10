package require models
package require runs

source category.tcl

set ::valid_sample_size 10000

azcat -no-tune Crafts Arts_Crafts_and_Sewing
azcat -no-tune Auto Automotive
azcat -no-tune Baby Baby_Products
azcat -no-tune Beauty Beauty_and_Personal_Care
azcat -no-tune Books Books
azcat -no-tune CDV CDs_and_Vinyl
azcat -no-tune Cell Cell_Phones_and_Accessories
# Clothing: Clothing_Shoes_and_Jewelry
azcat -no-tune Elec Electronics
azcat -no-tune Grocery Grocery_and_Gourmet_Food
azcat -no-tune HealthHouse Health_and_Household
# HomeKitchen: Home_and_Kitchen
azcat -no-tune IndSci Industrial_and_Scientific
azcat -no-tune Kindle Kindle_Store
azcat -no-tune MovTV Movies_and_TV
azcat -no-tune MusInst Musical_Instruments
azcat -no-tune Office Office_Products
azcat -no-tune PLG Patio_Lawn_and_Garden
azcat -no-tune Pet Pet_Supplies
azcat -no-tune Software Software
azcat -no-tune Sports Sports_and_Outdoors
azcat -no-tune THI Tools_and_Home_Improvement
azcat -no-tune Toys Toys_and_Games
azcat VidGames Video_Games

stage collect-stats {
    cmd lenskit codex sql -f bench-stats.sql stats.duckdb
    out stats.duckdb
    dep bench-stats.sql
    dep {*}[lsort [glob data/*.csv.gz]]
}
