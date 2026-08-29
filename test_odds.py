from odds_service import fetch_nba_player_props, build_consensus_lines

props = fetch_nba_player_props()
consensus = build_consensus_lines(props)

print("RAW ROWS:", len(props))
print("CONSENSUS ROWS:", len(consensus))

print("\nPOINTS")
print(consensus[consensus["market"] == "PTS"].head(20).to_string(index=False))

print("\nASSISTS")
print(consensus[consensus["market"] == "AST"].head(20).to_string(index=False))

print("\nREBOUNDS")
print(consensus[consensus["market"] == "REB"].head(20).to_string(index=False))
