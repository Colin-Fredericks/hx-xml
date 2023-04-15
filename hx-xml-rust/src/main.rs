// Include the minidom library for xml
extern crate minidom;
// Import the standard library
use std::fs::File;
use std::io::BufReader;
// Import the minidom library
use minidom::Element;


fn main() {

    // Instructions
    let instructions = r#""
    To use:
    cargo run choice path/to/video/folder -options
    
    Set your choice as...
      "true" to allow downloads of videos and transcripts for every video.
      "false" to disallow downloads of videos and transcripts for every video.
      "transcript" to allow only transcripts to be downloaded.
      "video" to allow only videos to be downloaded.
      "reset" to clear this attribute and let the edX defaults take over.
    
    Options:
      -h   Print this message and exit
    
    Last update: April 15th 2023
    "#;

    // Read in command line arguments
    let args: Vec<String> = std::env::args().collect();
    // If there are no arguments, print an error message and exit
    if args.len() < 2 {
        println!("Error: No arguments provided.");
        println!("{}", instructions);
        std::process::exit(1);
    }

    // First argument is the choice of downloads available
    let choice = &args[1];
    // Second argument is the path to the video folder
    let path = &args[2];

    // For now, just print out the arguments
    println!("Choice: {}", choice);
    println!("Path: {}", path);

    // And we're done.

}
