CLEAN_FILES := process_0_state.json process_1_state.json process_2_state.json process_3_state.json process_4_state.json

.PHONY: clean

clean:
	@echo "Cleaning process state files..."
	rm -f process_*_state.json
	@echo "Cleaning complete"