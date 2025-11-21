from migrate import read_pass, process_pass, write_pass


def main():
    raw_content = read_pass("example-entry")
    if raw_content:
        print(f"Raw content: {raw_content}")
        processed = process_pass("example-entry", raw_content)
        print(f"Processed: {processed}")

        # Test CSV writing with the single processed entry
        test_output_file = "~/.proton-migrate/test-output.csv"
        write_pass(test_output_file, [processed])
        print(f"Test CSV written to: {test_output_file}")
        print("CSV writing test completed successfully!")
    else:
        print("Failed to read pass entry")

if __name__ == '__main__':
    main()
