use std::env;
use std::io::{self, Read, Write};

const RAMP: &[u8] = b" .,:;irsXA253hMHGS#9B&@";

struct Options {
    width: usize,
    height: usize,
    cols: usize,
    rows: usize,
    color: bool,
    gamma: f32,
    trail: f32,
}

fn usage() -> ! {
    eprintln!("usage: mira-ascii-video --width PIXELS --height PIXELS [--cols N] [--rows N] [--mono] [--gamma N] [--trail N]");
    eprintln!("reads consecutive rgb24 frames from stdin and writes ANSI ASCII frames to stdout");
    std::process::exit(2);
}

fn value(args: &[String], index: &mut usize) -> usize {
    *index += 1;
    args.get(*index).and_then(|v| v.parse().ok()).unwrap_or_else(|| usage())
}

fn decimal(args: &[String], index: &mut usize) -> f32 {
    *index += 1;
    args.get(*index).and_then(|v| v.parse().ok()).unwrap_or_else(|| usage())
}

fn options() -> Options {
    let args: Vec<String> = env::args().collect();
    let mut width = None;
    let mut height = None;
    let mut cols = 80;
    let mut rows = None;
    let mut color = true;
    let mut gamma = 0.65;
    let mut trail = 0.20;
    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "--width" | "-w" => width = Some(value(&args, &mut i)),
            "--height" | "-h" => height = Some(value(&args, &mut i)),
            "--cols" | "-c" => cols = value(&args, &mut i),
            "--rows" | "-r" => rows = Some(value(&args, &mut i)),
            "--mono" => color = false,
            "--gamma" => gamma = decimal(&args, &mut i),
            "--trail" => trail = decimal(&args, &mut i),
            "--help" => usage(),
            _ => usage(),
        }
        i += 1;
    }
    let width = width.unwrap_or_else(|| usage());
    let height = height.unwrap_or_else(|| usage());
    if width == 0 || height == 0 || cols == 0 {
        usage();
    }
    // Terminal cells are roughly twice as tall as they are wide.
    let rows = rows.unwrap_or_else(|| ((cols * height) / (width * 2)).max(1));
    if !(0.1..=3.0).contains(&gamma) || !(0.0..1.0).contains(&trail) {
        usage();
    }
    Options { width, height, cols, rows, color, gamma, trail }
}

fn glyph(luma: u16, gamma: f32) -> char {
    let lifted = ((f32::from(luma) / 255.0).powf(gamma) * 255.0).round() as usize;
    let index = (lifted.min(255) * (RAMP.len() - 1)) / 255;
    RAMP[index] as char
}

#[derive(Clone, Copy)]
struct Cell(u8, u8, u8, u16);

fn sample(frame: &[u8], opt: &Options, x: usize, y: usize) -> (u8, u8, u8, u16) {
    let x0 = x * opt.width / opt.cols;
    let x1 = ((x + 1) * opt.width / opt.cols).max(x0 + 1).min(opt.width);
    let y0 = y * opt.height / opt.rows;
    let y1 = ((y + 1) * opt.height / opt.rows).max(y0 + 1).min(opt.height);
    let mut red = 0u32;
    let mut green = 0u32;
    let mut blue = 0u32;
    let mut count = 0u32;
    for py in y0..y1 {
        for px in x0..x1 {
            let offset = (py * opt.width + px) * 3;
            red += u32::from(frame[offset]);
            green += u32::from(frame[offset + 1]);
            blue += u32::from(frame[offset + 2]);
            count += 1;
        }
    }
    let r = (red / count) as u8;
    let g = (green / count) as u8;
    let b = (blue / count) as u8;
    let luma = ((77 * u16::from(r) + 150 * u16::from(g) + 29 * u16::from(b)) >> 8).min(255);
    (r, g, b, luma)
}

fn render(frame: &[u8], opt: &Options, previous: Option<&[Cell]>, out: &mut impl Write) -> io::Result<Vec<Cell>> {
    write!(out, "\x1b[H")?;
    let mut cells = Vec::with_capacity(opt.cols * opt.rows);
    for y in 0..opt.rows {
        for x in 0..opt.cols {
            let (r, g, b, luma) = sample(frame, opt, x, y);
            let index = y * opt.cols + x;
            let cell = if let Some(old) = previous.and_then(|cells| cells.get(index)) {
                let blend = |now: u8, before: u8| ((f32::from(now) * (1.0 - opt.trail)) + (f32::from(before) * opt.trail)).round() as u8;
                Cell(blend(r, old.0), blend(g, old.1), blend(b, old.2), blend(luma as u8, old.3 as u8) as u16)
            } else {
                Cell(r, g, b, luma)
            };
            if opt.color {
                write!(out, "\x1b[38;2;{};{};{}m", cell.0, cell.1, cell.2)?;
            }
            write!(out, "{}", glyph(cell.3, opt.gamma))?;
            cells.push(cell);
        }
        writeln!(out, "\x1b[0m")?;
    }
    out.flush()?;
    Ok(cells)
}

fn main() -> io::Result<()> {
    let opt = options();
    let frame_size = opt.width * opt.height * 3;
    let mut input = io::stdin().lock();
    let mut output = io::stdout().lock();
    let mut frame = vec![0; frame_size];
    let mut previous = None;
    write!(output, "\x1b[2J\x1b[?25l")?;
    loop {
        match input.read_exact(&mut frame) {
            Ok(()) => previous = Some(render(&frame, &opt, previous.as_deref(), &mut output)?),
            Err(error) if error.kind() == io::ErrorKind::UnexpectedEof => break,
            Err(error) => return Err(error),
        }
    }
    write!(output, "\x1b[0m\x1b[?25h")?;
    output.flush()
}
